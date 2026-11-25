from datetime import date
from pyluach.dates import GregorianDate, HebrewDate
from pyluach.hebrewcal import Month, Year

HEBREW_MONTHS = [
    (1, "Nisan"),
    (2, "Iyar"),
    (3, "Sivan"),
    (4, "Tammuz"),
    (5, "Av"),
    (6, "Elul"),
    (7, "Tishrei"),
    (8, "Cheshvan"),
    (9, "Kislev"),
    (10, "Tevet"),
    (11, "Shevat"),
    (12, "Adar"),
    (13, "Adar II"),
]

MONTH_NAME = dict(HEBREW_MONTHS)


def current_hebrew_year():
    t = date.today()
    return GregorianDate(t.year, t.month, t.day).to_heb().year


def is_leap(h_year):
    return Year(h_year).leap


def _month_length(hy, m):
    try:
        return len(Month(hy, m))
    except Exception:
        return 30


def occurrences(entry, start_hy, end_hy):
    """Yield (hebrew_year, gregorian_date) pairs for each hebrew year in range."""
    month = entry["hebrew_month"]
    day = entry["hebrew_day"]
    event_type = entry["event_type"]

    for hy in range(start_hy, end_hy + 1):
        m = month
        leap = is_leap(hy)
        # Adar in non-leap -> 12. In leap years, 12 = Adar I, 13 = Adar II.
        # Yahrzeits and birthdays from a non-leap Adar are observed in Adar II.
        if m == 12 and leap and event_type in ("yahrzeit", "birthday"):
            m = 13
        elif m == 13 and not leap:
            m = 12

        mlen = _month_length(hy, m)
        use_day = day if day <= mlen else mlen

        try:
            hd = HebrewDate(hy, m, use_day)
        except Exception:
            continue

        yield hy, hd.to_pydate()
