import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones

from flask import Flask, Response, abort, redirect, render_template, request, url_for
from pyluach.dates import GregorianDate

import db
import hebrew

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "/data/hebcal.db")
HORIZON_YEARS = int(os.environ.get("HORIZON_YEARS", "100"))

db.init(DB_PATH)


def detect_system_tz():
    env_tz = os.environ.get("TZ")
    if env_tz:
        try:
            ZoneInfo(env_tz)
            return env_tz
        except Exception:
            pass
    try:
        with open("/etc/timezone") as f:
            tz = f.read().strip()
            ZoneInfo(tz)
            return tz
    except Exception:
        pass
    return "UTC"


def active_tz():
    saved = db.get_setting(DB_PATH, "timezone")
    name = saved or detect_system_tz()
    try:
        return name, ZoneInfo(name)
    except Exception:
        return "UTC", ZoneInfo("UTC")


def _enrich(entries, horizon=3):
    current_hy = hebrew.current_hebrew_year()
    out = []
    for e in entries:
        preview = [g for _, g in hebrew.occurrences(e, current_hy, current_hy + horizon)]
        e["preview"] = preview[:3]
        e["month_name"] = hebrew.MONTH_NAME.get(e["hebrew_month"], "?")
        out.append(e)
    return out


def _form_data():
    mode = request.form.get("input_mode", "hebrew")
    if mode == "gregorian":
        g_str = request.form["gregorian_date"]
        y, mo, d = [int(p) for p in g_str.split("-")]
        pyd = date(y, mo, d)
        if request.form.get("after_sunset"):
            pyd = pyd + timedelta(days=1)
        hd = GregorianDate(pyd.year, pyd.month, pyd.day).to_heb()
        h_month, h_day = hd.month, hd.day
    else:
        h_month = int(request.form["hebrew_month"])
        h_day = int(request.form["hebrew_day"])
    return {
        "name": request.form["name"].strip(),
        "event_type": request.form["event_type"],
        "hebrew_month": h_month,
        "hebrew_day": h_day,
        "notes": request.form.get("notes", "").strip(),
    }


@app.route("/")
def index():
    entries = _enrich(db.list_entries(DB_PATH))
    return render_template("index.html", entries=entries, months=hebrew.HEBREW_MONTHS)


@app.route("/entries", methods=["POST"])
def create_entry():
    db.add_entry(DB_PATH, _form_data())
    return redirect(url_for("index"))


@app.route("/entries/<int:eid>/edit")
def edit_entry(eid):
    e = db.get_entry(DB_PATH, eid)
    if not e:
        abort(404)
    return render_template("edit.html", entry=e, months=hebrew.HEBREW_MONTHS)


@app.route("/entries/<int:eid>", methods=["POST"])
def mutate_entry(eid):
    method = request.form.get("_method", "POST").upper()
    if method == "DELETE":
        db.delete_entry(DB_PATH, eid)
    else:
        db.update_entry(DB_PATH, eid, _form_data())
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        tz = request.form.get("timezone", "").strip()
        if tz == "" or tz in available_timezones():
            db.set_setting(DB_PATH, "timezone", tz)
        return redirect(url_for("settings"))
    tz_name, _ = active_tz()
    return render_template(
        "settings.html",
        current_tz=tz_name,
        saved_tz=db.get_setting(DB_PATH, "timezone") or "",
        system_tz=detect_system_tz(),
        timezones=sorted(available_timezones()),
        horizon=HORIZON_YEARS,
    )


@app.route("/calendar.ics")
def calendar_ics():
    entries = db.list_entries(DB_PATH)
    current_hy = hebrew.current_hebrew_year()
    body = _build_ics(entries, current_hy, current_hy + HORIZON_YEARS)
    return Response(body, mimetype="text/calendar")


def _escape_ics(s):
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _title(entry):
    prefix = {"yahrzeit": "Yahrzeit", "birthday": "Hebrew birthday"}.get(entry["event_type"], "")
    return f"{prefix}: {entry['name']}" if prefix else entry["name"]


def _build_ics(entries, start_hy, end_hy):
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//hebcal-truenas//EN",
        "CALSCALE:GREGORIAN",
    ]
    for entry in entries:
        for hy, g in hebrew.occurrences(entry, start_hy, end_hy):
            uid = f"{entry['id']}-{hy}@hebcal-truenas"
            end = g + timedelta(days=1)
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART;VALUE=DATE:{g.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
                f"SUMMARY:{_escape_ics(_title(entry))}",
            ]
            notes = entry.get("notes") or ""
            if notes:
                lines.append(f"DESCRIPTION:{_escape_ics(notes)}")
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
