#!/usr/bin/env python3
"""List the files in a folder that changed in the last few days.

"Changed" means the modified time that Windows shows as "Date
modified": the last time the file's contents were written. The tool
walks a folder, compares each file's modified time with the time now,
and lists the files inside the window, newest first.

A day means 24 hours here, not a calendar date. A file written
yesterday at 23:00 is one day old at 07:00 the next morning, even
though the calendar date changed.

The tool only reads the folder. It has no code that creates, changes,
moves or deletes anything.
"""

import os
import sys
import time

DAY = 24 * 60 * 60


def scan(folder, days, now=None):
    """Find files in folder modified within the last days days.

    Returns (checked, recent, errors):
    checked - how many files were looked at
    recent  - list of (age_in_seconds, relative_path), newest first
    errors  - how many files or folders could not be read
    """
    if now is None:
        now = time.time()
    checked = 0
    recent = []
    errors = []

    def on_error(exc):
        errors.append(exc)

    for dirpath, _dirnames, filenames in os.walk(folder, onerror=on_error):
        for name in filenames:
            path = os.path.join(dirpath, name)
            checked += 1
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                errors.append(path)
                continue
            age = now - mtime
            if age <= days * DAY:
                rel = os.path.relpath(path, folder)
                recent.append((age, rel))
    recent.sort()
    return checked, recent, errors


def describe(age):
    """A short age description in whole days."""
    if age < 0:
        return "a future date"
    days = int(age // DAY)
    if days == 0:
        return "today"
    if days == 1:
        return "1 day ago"
    return "{} days ago".format(days)


def main(argv):
    if len(argv) not in (2, 3):
        print("Usage: python recent.py FOLDER [DAYS]")
        print("Lists the files in FOLDER changed in the last DAYS days")
        print("(7 if you do not say), newest first.")
        return 2
    folder = argv[1]
    if not os.path.isdir(folder):
        print("Not a folder: " + folder)
        return 1
    days = 7
    if len(argv) == 3:
        try:
            days = int(argv[2])
        except ValueError:
            print("DAYS must be a whole number, not: " + argv[2])
            return 1
        if days < 1:
            print("DAYS must be at least 1.")
            return 1
    checked, recent, errors = scan(folder, days)
    print("Recent files report")
    print("Folder: " + folder)
    print("Window: the last {} day(s)".format(days))
    print("Checked: {} file(s)".format(checked))
    if recent:
        print("")
        print("Changed inside the window:")
        for age, rel in recent:
            print("{}  {}".format(describe(age), rel))
    else:
        print("Nothing changed inside the window.")
    if errors:
        print("")
        print("Note: {} file(s) or folder(s) could not be read.".format(len(errors)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
