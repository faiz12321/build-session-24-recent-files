#!/usr/bin/env python3
"""Make a small made-up folder for the recent files lesson.

Each file is given a changed time on purpose: some inside the last
week, one older, one in the future. The times are set half a day
off the exact day boundaries so the report reads the same whether
you run it now or in a few minutes. Nothing here is real.
"""

import datetime
import os
import time

DAY = 24 * 60 * 60
NOW = time.time()

FILES = [
    ("notes.txt", 0.5, "Shopping: milk, bread, coffee.\n"),
    ("draft letter.txt", 2.5, "Dear aunt, thank you for the...\n"),
    ("photos todo.txt", 6.5, "Print the holiday photos.\n"),
    ("old tax notes.txt", 40.0, "2019 figures, keep for reference.\n"),
]


def main():
    base = "sample"
    os.makedirs(base, exist_ok=True)
    for name, age_days, text in FILES:
        path = os.path.join(base, name)
        with open(path, "w") as handle:
            handle.write(text)
        moment = NOW - age_days * DAY
        os.utime(path, (moment, moment))
    future = os.path.join(base, "backup.log")
    with open(future, "w") as handle:
        handle.write("backup finished\n")
    moment = NOW + 2 * DAY
    os.utime(future, (moment, moment))
    late = os.path.join(base, "late notes.txt")
    with open(late, "w") as handle:
        handle.write("Written just before midnight.\n")
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    moment = datetime.datetime(yesterday.year, yesterday.month,
                               yesterday.day, 23, 59).timestamp()
    os.utime(late, (moment, moment))
    print("Made sample/ with 6 files.")
    print("Changed times are made up: today, yesterday at 23:59, 2 and")
    print("6 days ago, 40 days ago, and one file dated two days ahead.")


if __name__ == "__main__":
    main()
