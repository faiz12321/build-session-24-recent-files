#!/usr/bin/env python3
"""List the files in a folder that changed in the last few days.

"Changed" means the modified time that Windows shows as "Date
modified": the last time the file's contents were written. The tool
walks a folder, compares each file's modified time with the time now,
and lists the files inside the window, newest first.

A day means 24 hours here, not a calendar date. A file written
yesterday at 23:00 is only eight hours old at 07:00 the next morning,
even though the calendar date changed.

The tool only reads the folder. It has no code that creates, changes,
moves or deletes anything.
"""

import os
import sys
import stat
from pathlib import Path
import time

DAY = 24 * 60 * 60


class UnsafePathError(OSError):
    """An unsupported path, distinct from a filesystem read error."""


def safe_input(value, directory=False):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise UnsafePathError('Parent-traversal paths are unsupported.')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 0x400:
            raise UnsafePathError('Links/reparse points are unsupported.')
    info = path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise UnsafePathError('Expected an ordinary directory.')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise UnsafePathError('Expected an ordinary singly linked file.')
    return path


def scan(folder, days, now=None):
    """Find files in folder modified within the last days days.

    Returns (checked, recent, errors):
    checked - how many files were looked at
    recent  - list of (age_in_seconds, relative_path), newest first
    errors  - how many files or folders could not be read
    """
    if now is None:
        now = time.time()
    folder = safe_input(folder, directory=True)
    checked = 0
    recent = []
    errors = []
    total = 0
    stack = [folder]
    while stack:
        current = stack.pop()
        safe_input(current, directory=True)
        try:
            with os.scandir(current) as entries:
                ordered = sorted(entries, key=lambda entry: entry.name)
        except OSError as error:
            errors.append(error)
            continue
        for entry in ordered:
            total += 1
            if total > 10000:
                raise OSError('More than 10000 entries; refusing this tree.')
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as error:
                checked += 1
                errors.append(error)
                continue
            directory = stat.S_ISDIR(info.st_mode)
            if not directory:
                checked += 1
            try:
                child = safe_input(entry.path, directory=directory)
            except UnsafePathError:
                raise
            except OSError as error:
                errors.append(error)
                continue
            if directory:
                stack.append(child)
                continue
            try:
                mtime = os.stat(child).st_mtime
            except OSError as error:
                errors.append(error)
                continue
            age = now - mtime
            if age <= days * DAY:
                recent.append((age, os.path.relpath(child, folder)))
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
    try:
        checked, recent, errors = scan(folder, days)
    except OSError as error:
        print('Could not read: ' + str(error))
        return 2
    print("Recent files report")
    print("Folder: " + folder)
    print("Window: the last {} day(s)".format(days))
    print("Checked: {} file(s)".format(checked))
    if recent:
        print("")
        print("Changed inside the window:")
        for age, rel in recent:
            print("{}  {}".format(describe(age), rel))
    elif not errors:
        print("Nothing changed inside the window.")
    else:
        print("Incomplete scan: unvisited files may be inside the window.")
    if errors:
        print("")
        print("Note: {} file(s) or folder(s) could not be read.".format(len(errors)))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
