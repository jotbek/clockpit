"""Polish local time from the UTC RTC used by NTP and the simulator."""


def day_of_week(year, month, day):
    if month < 3:
        month += 12
        year -= 1
    century, within = year // 100, year % 100
    return (day + 13 * (month + 1) // 5 + within + within // 4
            + century // 4 - 2 * century + 5) % 7


def is_dst_poland(year, month, day, hour):
    # Both EU transitions take place at 01:00 UTC on the last Sunday.
    if 3 < month < 10:
        return True
    if month != 3 and month != 10:
        return False
    last_sunday = 31 - (day_of_week(year, month, 31) + 1) % 7
    after_transition = day > last_sunday or (day == last_sunday and hour >= 1)
    return after_transition if month == 3 else not after_transition


def local_seconds(utc):
    offset = 2 if is_dst_poland(utc[0], utc[1], utc[2], utc[3]) else 1
    return ((utc[3] + offset) % 24) * 3600 + utc[4] * 60 + utc[5]
