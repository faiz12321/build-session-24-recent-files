# Find the files that changed in the last few days

A small read-only Python tool built step by step. Give it a folder and it lists the files whose modified time - "Date modified" in Windows - falls inside the last few days, newest first. Seven days by default, or a number you give. The tool never changes, moves or deletes anything.

Python's os documentation says a file's `st_mtime` is the time of its most recent content modification, measured in seconds. The tool compares that with the current time, so a day means 24 hours, not a calendar date: a file written yesterday at 23:00 is one day old at 07:00 the next morning.

## Run it

    python make_sample.py       # makes a small made-up folder in sample/
    python recent.py sample     # files changed in the last 7 days
    python recent.py sample 30  # files changed in the last 30 days
    python -m unittest -v       # twenty-three automated tests

On Windows, if `python` is not found, use `py`.

## Files

- `recent.py` - the tool
- `make_sample.py` - makes five made-up files with known changed times
- `test_recent.py` - tests

## Notes

- Ages are whole days rounded down: 2 days and 3 hours shows as "2 days ago". A file less than a day old shows as "today".
- A file dated in the future (it happens, for example after a wrong clock) is listed as "a future date".
- The window edge is inclusive: a file exactly 7 times 24 hours old is inside a 7 day window.
- Times are compared in seconds, so the answer does not depend on calendar dates or time zones.
- The tool uses Python's os.walk, which by default does not follow links into other folders.
- Files or folders that cannot be read are counted and mentioned in the report.
- The tool only reads the folder. Tests check that nothing is changed or created, including changed times.
- Tested only on small made-up folders. Python 3.10 and 3.12 on Linux, and, by GitHub Actions, Python 3.12 on Windows and Ubuntu. Not tested on a Windows 10 or 11 desktop or on real folders.
- Educational example, no warranty. Use at your own risk.
- Code is MIT licensed (see LICENSE). Python belongs to its owners; this repository does not include it.
