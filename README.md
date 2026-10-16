# Find the files that changed in the last few days

A small read-only Python tool built step by step. Give it a folder and it lists the files whose modified time - "Date modified" in Windows - falls inside the last few days, newest first. Seven days by default, or a number you give. The tool never changes, moves or deletes anything.

Python's os documentation says a file's `st_mtime` is the time of its most recent content modification, measured in seconds. The tool compares that with the current time, so a day means 24 hours, not a calendar date: a file written yesterday at 23:00 is only eight hours old at 07:00 the next morning.

## Run it

    python make_sample.py       # makes a small made-up folder in sample/
    python recent.py sample     # files changed in the last 7 days
    python recent.py sample 30  # files changed in the last 30 days
    python -m unittest -v       # 38 small fixture tests

On Windows, if `python` is not found, use `py`.

## Files

- `recent.py` - the tool
- `make_sample.py` - makes six made-up files with known changed times
- `test_recent.py` - tests

## Notes

- Ages are whole days rounded down: 2 days and 3 hours shows as "2 days ago". A file less than a day old shows as "today".
- A file dated in the future (it happens, for example after a wrong clock) is listed as "a future date".
- The window edge is inclusive: a file exactly 7 times 24 hours old is inside a 7 day window.
- Times are compared in seconds, so the answer does not depend on calendar dates or time zones.
- The final checker refuses unsafe links/reparse/hardlinks/special entries and traversal. Enumeration and metadata errors produce visible incomplete status and exit 2, not a false clean report.
- Files or folders that cannot be read make a visible incomplete report and exit 2.
- The tool only reads the folder. Tests check that nothing is changed or created, including changed times.
- Tested only on small made-up folders. Python 3.10 and 3.12 on Linux, and, by GitHub Actions, Python 3.12 on Windows and Ubuntu. No real-folder or desktop Windows proof.
- Educational example, no warranty. Use at your own risk.
- Code is MIT licensed (see LICENSE). Python belongs to its owners; this repository does not include it.

## Repaired setup and limits

Setup exclusively creates a NEW tiny fictional sample folder/six files and sets times only on its new outputs. Existing paths and traversal/linked/reparse parents refuse. Partial setup remains on failure; use another new lesson folder. No reset. Final checker caps 10000 entries; memory/time costs remain. Stop editors/sync; no hostile-race sandbox. Names/paths may be private. Modified times are metadata, not proof of a person's work; future times stay included and labeled.

## Replay evidence

Two Windows and two Ubuntu full replays run the exact visible source. 38 tests pass, with one Windows skip (Unix pipe). Both exercise symlinks. Pairs differ only in unittest time. Displayed output is first Windows run. Recorder uses and removes only its own temporary lesson folder.
NEW sample setup exclusively creates six tiny fictional files and sets times only on these new outputs. Existing/traversal/linked-parent paths refuse; repeat is not a reset. Partial setup remains on failure; use another new folder. Final checker refuses unsafe input/ancestor/tree links/reparse/hardlinks/special entries and traversal. Enumeration/metadata errors produce visible incomplete status and exit 2 rather than false clean. Cap 10000 entries; listing/files still consume memory/time. Stop editors/sync; no hostile-race guarantee.
38 small tests: original 23 age/window/report cases, four setup-preservation and eleven filesystem/error cases. One regression forces metadata-preflight failure on every platform; it caught a real Windows error path in review. Symlink creation can skip where unavailable. No real-folder or desktop Windows proof.
The tool compares modified-time metadata in seconds, with inclusive cutoff and 24-hour days. Metadata can be copied or changed and does not prove who worked on a file. Future times stay included and labeled. Output ages/ordering depend on clock and file metadata. Read-only checker has no write/network code; paths and times may be private, and other software/sync is uncontrolled.
