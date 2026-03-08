import os
import re
import sys
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import eel
import ctypes
from i18n import msgs

# Fix for taskbar icon on Windows
try:
    myappid = "firo.conversor.mensajes.v2"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# ==============================
# Helper Functions
# ==============================
IGNORED_MSGS = [
    "imagen omitida",
    "audio omitido",
    "sticker omitido",
    "video omitido",
    "gif omitido",
    "documento omitido",
    "image omitted",
    "audio omitted",
    "sticker omitted",
    "video omitted",
    "gif omitted",
    "document omitted",
    "<media omitted>",
    "<multimedia omitido>",
]


def parse_time(t_str):
    t_str = (
        t_str.strip()
        .replace("a. m.", "AM")
        .replace("p. m.", "PM")
        .replace("a.m.", "AM")
        .replace("p.m.", "PM")
    )
    formats = ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p", "%I:%M%p", "%I:%M:%S%p"]
    for fmt in formats:
        try:
            return datetime.strptime(t_str, fmt)
        except ValueError:
            pass
    return None


def parse_date_txt(d_str, hint_format="DD/MM"):
    d_str = d_str.strip().replace("-", "/")
    factors = d_str.split("/")
    if len(factors) == 3 and len(factors[2]) == 2:
        year = int(factors[2])
        factors[2] = str(2000 + year) if year < 80 else str(1900 + year)
        d_str = "/".join(factors)

    formats = (
        ["%d/%m/%Y", "%Y/%m/%d"] if hint_format == "DD/MM" else ["%m/%d/%Y", "%Y/%m/%d"]
    )
    for fmt in formats:
        try:
            return datetime.strptime(d_str, fmt)
        except ValueError:
            pass
    return None


def parse_date_ui(d_str):
    fmt = "%d/%m/%Y"  # Hardcoded spanish for now
    try:
        return datetime.strptime(d_str.strip(), fmt)
    except ValueError:
        return None


# ==============================
# Global State
# ==============================
app_state = {"filepath": "", "unique_names": [], "parsed_cache": []}

eel.init("web")


@eel.expose
def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Seleccionar chat TXT", filetypes=[("Text Files", "*.txt")]
    )
    root.destroy()

    if not path:
        return {"success": False}

    app_state["filepath"] = path
    default_out = os.path.join(os.path.dirname(path), "chat.html")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    msg_regex = re.compile(
        r"^\[?(\d{1,4}[/-]\d{1,4}[/-]\d{1,4})[,\]\-\s]+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[aApP]\.?[mM]\.?)?)\]?\s*(?:-\s*)?([^:]+?):\s+(.*)$",
        re.IGNORECASE,
    )

    app_state["unique_names"] = []
    app_state["parsed_cache"] = []
    app_names = set()
    current_msg = None

    guessed_format = "DD/MM"
    for line in lines:
        line_str = line.replace("\u200e", "").replace("\u200f", "").strip("\n\r")
        match = msg_regex.match(line_str)
        if match:
            d_str = match.groups()[0].replace("-", "/")
            factors = d_str.split("/")
            if len(factors) == 3:
                try:
                    if int(factors[0]) > 12:
                        guessed_format = "DD/MM"
                        break
                    elif int(factors[1]) > 12:
                        guessed_format = "MM/DD"
                        break
                except:
                    pass

    for line in lines:
        line_str = line.replace("\u200e", "").replace("\u200f", "").strip("\n\r")
        if not line_str:
            if current_msg:
                current_msg["text"] += "\n"
            continue

        match = msg_regex.match(line_str)
        if match:
            if current_msg:
                app_state["parsed_cache"].append(current_msg)
            date_str, time_str, sender, text = match.groups()
            app_names.add(sender.strip())

            current_msg = {
                "raw_date": date_str,
                "dt_date": parse_date_txt(date_str, hint_format=guessed_format),
                "raw_time": time_str,
                "dt_time": parse_time(time_str),
                "sender": sender.strip(),
                "text": text.strip(),
            }
        else:
            if current_msg:
                current_msg["text"] += "\n" + line_str

    if current_msg:
        app_state["parsed_cache"].append(current_msg)

    unique_names = list(app_names)
    unique_names.sort()
    app_state["unique_names"] = unique_names

    return {
        "success": True,
        "filepath": path,
        "default_out": default_out,
        "names": unique_names,
    }


@eel.expose
def select_output_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.asksaveasfilename(
        defaultextension=".html",
        filetypes=[("HTML files", "*.html")],
        title="Guardar como",
    )
    root.destroy()
    return path


@eel.expose
def generate_html(config):
    lang = config.get("lang", "es")
    t = msgs.get(lang, msgs["es"])

    if not app_state["filepath"]:
        return {"error": t["no_file"]}

    p_A = config.get("person_a")
    p_B = config.get("person_b")

    if not p_A or not p_B or p_A in ["No detectado", "Not detected"]:
        return {"error": t["invalid_part"]}

    date_filters = []
    for f in config.get("date_filters", []):
        ds, de = f.get("start"), f.get("end")
        dt_s = parse_date_ui(ds) if ds else None
        dt_e = parse_date_ui(de) if de else None
        if ds and not dt_s:
            return {"error": f"{t['invalid_date']}{ds}"}
        if de and not dt_e:
            return {"error": f"{t['invalid_date']}{de}"}
        if dt_s or dt_e:
            date_filters.append((dt_s, dt_e))

    use_12h = config.get("time_format") == "12H"
    is_compact = config.get("ui_density") == "Compacto"
    size_str = config.get("text_size")
    columns = int(config.get("columns", 1))

    margin = "4px" if is_compact else "10px"
    padding = "6px" if is_compact else "10px"
    chip_margin = "4px auto" if is_compact else "12px auto"
    f_size = "14px" if is_compact else "15px"
    time_size = "10px" if is_compact else "11px"

    ds_margin_top = "1rem" if is_compact else "2rem"
    ds_padding_top = "1rem" if is_compact else "2rem"
    ds_padding_bottom = "1rem"

    if size_str == "Grande":
        f_size, time_size = "18px", "13px"
    elif size_str == "Pequeño":
        f_size, time_size = "13px", "9px"

    alias_A = config.get("alias_a") or p_A
    alias_B = config.get("alias_b") or p_B

    BG_COLOR = "#f5f2eb"
    MY_BUBBLE_COLOR = "#dcf8c6"
    OTHER_BUBBLE_COLOR = "#ffffff"
    TEXT_COLOR = "#111111"
    TIME_COLOR = "#6b6b6b"
    CHIP_BG = "#ffffff"
    CHIP_FG = "#333333"

    html_head = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: {BG_COLOR};
        color: {TEXT_COLOR};
        padding: 20px;
        margin: 0;
    }}
    .message {{
        margin: {margin};
        padding: {padding};
        border-radius: 12px;
        max-width: 80%;
        position: relative;
        font-size: {f_size};
        line-height: 1.4;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        word-wrap: break-word;
        clear: both;
    }}
    .sender {{ background: {MY_BUBBLE_COLOR}; float: right; border-top-right-radius: 0; }}
    .receiver {{ background: {OTHER_BUBBLE_COLOR}; float: left; border-top-left-radius: 0; }}
    .time {{ font-size: {time_size}; color: {TIME_COLOR}; text-align: right; margin-top: 4px; float: right; margin-left: 8px; }}
    .date-chip {{ display: inline-block; background: {CHIP_BG}; border-radius: 16px; padding: 8px 18px; font-size: 16px; font-weight: bold; color: {CHIP_FG}; box-shadow: 0 2px 5px rgba(0,0,0,0.2); margin: {chip_margin}; }}
    .date-separator {{ text-align: center; clear: both; border-top: 1px solid #0000001a; margin-top: {ds_margin_top}; padding-top: {ds_padding_top}; padding-bottom: {ds_padding_bottom}; }}
    .message-row {{ overflow: hidden; width: 100%; }}
    .text-content {{ white-space: pre-wrap; }}
    .author {{ font-weight: bold; font-size: 0.85em; margin-bottom: 4px; opacity: 0.85; }}
    .sender .author {{ color: #075e54; }}
    .receiver .author {{ color: #128c7e; }}
    """

    if columns > 1:
        html_head += f"#print-wrapper {{ column-count: {columns}; column-gap: 20px; width: 100%; break-inside: avoid; }} #print-wrapper > * {{ break-inside: avoid-column; }}"

    html_head += "</style>\n</head>\n<body>\n"
    if columns > 1:
        html_head += '<div id="print-wrapper">\n'

    html_body = ""
    last_date_str = None
    count = 0

    for msg in app_state["parsed_cache"]:
        m_dt = msg["dt_date"]
        # Filters
        if date_filters and m_dt:
            valid = False
            for start_d, end_d in date_filters:
                if start_d and m_dt < start_d:
                    continue
                if end_d and m_dt > end_d:
                    continue
                valid = True
                break
            if not valid:
                continue

        # Date Chip
        current_date_str = m_dt.strftime("%d/%m/%Y") if m_dt else msg["raw_date"]
        if current_date_str != last_date_str:
            fecha_humana = current_date_str
            if m_dt:
                try:
                    import locale

                    # Guardamos el locale actual
                    old_loc = locale.setlocale(locale.LC_TIME, None)
                    locale.setlocale(locale.LC_TIME, "")
                    fecha_humana = m_dt.strftime("%d de %B de %Y")
                    # Restauramos el locale
                    locale.setlocale(locale.LC_TIME, old_loc)
                except:
                    pass
            html_body += f'<div class="date-separator"><div class="date-chip">{fecha_humana}</div></div>\n'
            last_date_str = current_date_str

        snd = msg["sender"]
        css_class = "sender" if snd == p_A else "receiver"
        alias = alias_A if snd == p_A else (alias_B if snd == p_B else snd)

        m_time_dt = msg["dt_time"]
        if m_time_dt:
            if use_12h:
                ampm = "AM" if m_time_dt.hour < 12 else "PM"
                rendered_time = m_time_dt.strftime("%I:%M ") + ampm
            else:
                rendered_time = m_time_dt.strftime("%H:%M")
        else:
            rendered_time = msg["raw_time"]

        txt_lower = msg["text"].strip().lower()
        if txt_lower in IGNORED_MSGS or "<media omitted>" in txt_lower:
            continue

        clean_text = msg["text"].replace("<", "&lt;").replace(">", "&gt;")

        html_body += f'<div class="message-row"><div class="message {css_class}">'
        if config.get("show_name"):
            html_body += f'<div class="author">{alias}</div>'
        html_body += f'<div class="text-content">{clean_text}</div><div class="time">{rendered_time}</div></div></div>\n'
        count += 1

    html_foot = "</div>\n" if columns > 1 else ""
    html_foot += "</body>\n</html>"

    final_html = html_head + html_body + html_foot
    out_path = config.get("out_path", "").strip()
    if not out_path:
        return {"error": t["empty_path"]}

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_html)
        if config.get("auto_open"):
            webbrowser.open("file://" + os.path.realpath(out_path))
        return {"success": t["success"].format(count)}
    except Exception as e:
        return {"error": f"{t['error_save']}{str(e)}"}


@eel.expose
def is_frozen():
    return getattr(sys, "frozen", False)


if __name__ == "__main__":
    try:
        eel.start("index.html", size=(960, 640), port=0)
    except Exception as e:
        print("Error al abrir Eel:", e)
        # Fallback if preferred browser is not installed
        import time

        time.sleep(2)
