import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import make_sample
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "recent.py")

sys.path.insert(0, HERE)
import recent

DAY = 24 * 60 * 60


def run_tool(*args):
    return subprocess.run(
        [sys.executable, TOOL] + list(args),
        capture_output=True, text=True, timeout=60,
    )


def aged(root, name, age_days, base=None):
    path = os.path.join(root, name)
    with open(path, "w") as handle:
        handle.write("x\n")
    if base is None:
        base = __import__("time").time()
    moment = base - age_days * DAY
    os.utime(path, (moment, moment))
    return path


class DescribeTests(unittest.TestCase):
    def test_under_a_day_is_today(self):
        self.assertEqual(recent.describe(3600), "today")

    def test_one_full_day(self):
        self.assertEqual(recent.describe(DAY), "1 day ago")

    def test_several_days(self):
        self.assertEqual(recent.describe(6 * DAY), "6 days ago")

    def test_part_days_round_down(self):
        self.assertEqual(recent.describe(2 * DAY + 3600), "2 days ago")

    def test_future_is_called_out(self):
        self.assertEqual(recent.describe(-DAY), "a future date")


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.now = 1_700_000_000

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_inside_and_outside_the_window(self):
        aged(self.tmp, "new.txt", 2, base=self.now)
        aged(self.tmp, "old.txt", 40, base=self.now)
        checked, recent_, errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual(checked, 2)
        self.assertEqual([rel for _age, rel in recent_], ["new.txt"])
        self.assertEqual(errors, [])

    def test_exactly_at_the_edge_is_inside(self):
        aged(self.tmp, "edge.txt", 7, base=self.now)
        _checked, recent_, _errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual([rel for _age, rel in recent_], ["edge.txt"])

    def test_just_past_the_edge_is_outside(self):
        path = aged(self.tmp, "past.txt", 7, base=self.now)
        moment = self.now - 7 * DAY - 1
        os.utime(path, (moment, moment))
        _checked, recent_, _errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual(recent_, [])

    def test_newest_comes_first(self):
        aged(self.tmp, "two.txt", 2, base=self.now)
        aged(self.tmp, "five.txt", 5, base=self.now)
        aged(self.tmp, "one.txt", 1, base=self.now)
        _checked, recent_, _errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual([rel for _age, rel in recent_],
                         ["one.txt", "two.txt", "five.txt"])

    def test_nested_files_show_relative_paths(self):
        os.makedirs(os.path.join(self.tmp, "sub", "deep"))
        aged(os.path.join(self.tmp, "sub", "deep"), "inner.txt", 1, base=self.now)
        _checked, recent_, _errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual([rel for _age, rel in recent_],
                         [os.path.join("sub", "deep", "inner.txt")])

    def test_empty_folder(self):
        checked, recent_, errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual((checked, recent_, errors), (0, [], []))

    def test_a_file_that_cannot_be_counted_is_reported(self):
        aged(self.tmp, "new.txt", 1, base=self.now)
        aged(self.tmp, "mystery.txt", 1, base=self.now)
        real_stat = os.stat

        def fake_stat(path, *args, **kwargs):
            if "mystery.txt" in str(path):
                raise OSError("pretend the stat failed")
            return real_stat(path, *args, **kwargs)

        with mock.patch("os.stat", side_effect=fake_stat):
            checked, recent_, errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual(checked, 2)
        self.assertEqual([rel for _age, rel in recent_], ["new.txt"])
        self.assertEqual(len(errors), 1)

    def test_preflight_metadata_failure_is_reported(self):
        aged(self.tmp, "new.txt", 1, base=self.now)
        aged(self.tmp, "mystery.txt", 1, base=self.now)
        real_safe = recent.safe_input
        def fail(path, *args, **kwargs):
            if str(path).endswith("mystery.txt"):
                raise OSError("pretend preflight metadata failed")
            return real_safe(path, *args, **kwargs)
        with mock.patch.object(recent, "safe_input", side_effect=fail):
            checked, found, errors = recent.scan(self.tmp, 7, now=self.now)
        self.assertEqual(checked, 2)
        self.assertEqual([rel for age, rel in found], ["new.txt"])
        self.assertEqual(len(errors), 1)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_arguments_prints_usage(self):
        result = run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stdout)

    def test_missing_folder_is_a_clear_error(self):
        result = run_tool(os.path.join(self.tmp, "nope"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Not a folder:", result.stdout)

    def test_a_file_is_not_a_folder(self):
        path = aged(self.tmp, "note.txt", 1)
        result = run_tool(path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Not a folder:", result.stdout)

    def test_days_must_be_a_whole_number(self):
        for bad in ("abc", "7.5"):
            result = run_tool(self.tmp, bad)
            self.assertEqual(result.returncode, 1, bad)
            self.assertIn("whole number", result.stdout)

    def test_days_must_be_at_least_one(self):
        result = run_tool(self.tmp, "0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("at least 1", result.stdout)

    def test_report_shows_window_and_count(self):
        aged(self.tmp, "new.txt", 1)
        aged(self.tmp, "old.txt", 30)
        result = run_tool(self.tmp, "7")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Window: the last 7 day(s)", result.stdout)
        self.assertIn("Checked: 2 file(s)", result.stdout)
        self.assertIn("new.txt", result.stdout)
        self.assertNotIn("old.txt", result.stdout)

    def test_a_narrower_window_hides_older_files(self):
        aged(self.tmp, "new.txt", 1)
        aged(self.tmp, "week.txt", 6)
        wide = run_tool(self.tmp, "7")
        narrow = run_tool(self.tmp, "3")
        self.assertIn("week.txt", wide.stdout)
        self.assertNotIn("week.txt", narrow.stdout)
        self.assertIn("new.txt", narrow.stdout)

    def test_nothing_in_window_says_so(self):
        aged(self.tmp, "old.txt", 30)
        result = run_tool(self.tmp, "7")
        self.assertIn("Nothing changed inside the window.", result.stdout)

    def test_default_window_is_seven_days(self):
        aged(self.tmp, "week.txt", 6)
        aged(self.tmp, "month.txt", 30)
        result = run_tool(self.tmp)
        self.assertIn("Window: the last 7 day(s)", result.stdout)
        self.assertIn("week.txt", result.stdout)
        self.assertNotIn("month.txt", result.stdout)

    def test_tool_does_not_change_the_tree(self):
        aged(self.tmp, "new.txt", 1)
        before = []
        for dirpath, dirnames, filenames in os.walk(self.tmp):
            before.append((dirpath, sorted(dirnames), sorted(filenames)))
        path = os.path.join(self.tmp, "new.txt")
        moment = os.stat(path).st_mtime
        run_tool(self.tmp)
        after = []
        for dirpath, dirnames, filenames in os.walk(self.tmp):
            after.append((dirpath, sorted(dirnames), sorted(filenames)))
        self.assertEqual(before, after)
        self.assertEqual(os.stat(path).st_mtime, moment)
        with open(path) as handle:
            self.assertEqual(handle.read(), "x\n")

    def test_tool_has_no_write_code(self):
        with open(TOOL) as handle:
            source = handle.read()
        for word in ("os.remove", "os.rmdir", "os.rename", "shutil.rmtree",
                     "open(", "os.makedirs", "os.mkdir", "os.utime"):
            self.assertNotIn(word, source)


class SafeSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sample = self.root / 'sample'

    def test_existing_folder_preserves_nested_bytes_and_mtime(self):
        (self.sample / 'nested').mkdir(parents=True)
        keep = self.sample / 'nested' / 'keep'
        keep.write_bytes(b'KEEP')
        before = keep.read_bytes(), keep.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (keep.read_bytes(), keep.stat().st_mtime_ns))

    def test_existing_file_preserved(self):
        self.sample.write_bytes(b'KEEP')
        before = self.sample.read_bytes(), self.sample.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (self.sample.read_bytes(), self.sample.stat().st_mtime_ns))

    def test_repeat_preserves_every_output(self):
        make_sample.make(self.sample)
        before = {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()}
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()})

    def test_cli_repeat_preserves_every_output(self):
        import subprocess, sys
        script = self.root / 'make_sample.py'
        shutil.copyfile(Path(make_sample.__file__).resolve(), script)
        make_sample.make(self.sample)
        before = {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('sample already exists', result.stderr)
        self.assertEqual(before, {str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()})





class FilesystemSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.sample=self.root/'sample'
        with redirect_stdout(io.StringIO()):make_sample.make(self.sample)
    def run_check(self,path):
        output=io.StringIO()
        with redirect_stdout(output):code=recent.main(['recent.py',str(path)])
        return code,output.getvalue()
    def link(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError:self.skipTest('Symlink creation unavailable')
    def test_root_link_refused(self):
        link=self.root/'linked';self.link(link,self.sample,True)
        self.assertEqual(self.run_check(link)[0],2)
    def test_file_link_refused(self):
        self.link(self.sample/'link',self.sample/'notes.txt')
        self.assertEqual(self.run_check(self.sample)[0],2)
    def test_loop_refused(self):
        self.link(self.sample/'loop',self.sample,True)
        self.assertEqual(self.run_check(self.sample)[0],2)
    def test_hardlink_refused(self):
        os.link(self.sample/'notes.txt',self.sample/'hard')
        self.assertEqual(self.run_check(self.sample)[0],2)
    def test_pipe_refused(self):
        if not hasattr(os,'mkfifo'):self.skipTest('Unix pipe unavailable')
        os.mkfifo(self.sample/'pipe')
        self.assertEqual(self.run_check(self.sample)[0],2)
    def test_traversal_refused(self):
        self.assertEqual(self.run_check(self.sample/'..'/'sample')[0],2)
    def test_setup_linked_parent_refused(self):
        link=self.root/'linked';self.link(link,self.root,True)
        with self.assertRaises(OSError):make_sample.make(link/'new')
        self.assertFalse((self.root/'new').exists())
    def test_setup_traversal_refused(self):
        with self.assertRaises(OSError):make_sample.make(self.root/'..'/self.root.name/'new')
        self.assertFalse((self.root/'new').exists())
    def test_enumeration_error_returns_nonzero(self):
        with mock.patch('os.scandir',side_effect=PermissionError('simulated denial')):
            code,out=self.run_check(self.sample)
        self.assertEqual(code,2);self.assertIn('could not be read',out)
    def test_bytes_mtimes_preserved(self):
        before={str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()}
        self.run_check(self.sample)
        self.assertEqual(before,{str(p.relative_to(self.sample)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.rglob('*') if p.is_file()})


if __name__ == "__main__":
    unittest.main()
