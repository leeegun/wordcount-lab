"""wordcount.py 테스트 (표준 라이브러리 unittest).

실행: python -m unittest discover -s test -v
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wordcount  # noqa: E402


def run(*argv, stdin=None):
    """main()을 실행하고 (종료코드, stdout, stderr)를 돌려준다."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        if stdin is not None:
            with mock.patch("sys.stdin", io.StringIO(stdin)):
                code = wordcount.main(list(argv))
        else:
            code = wordcount.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CountTextTest(unittest.TestCase):
    def test_basic(self):
        s = wordcount.count_text("Hello world, hello!\n")
        self.assertEqual((s["lines"], s["words"], s["chars"]), (1, 3, 20))

    def test_korean(self):
        self.assertEqual(wordcount.count_text("안녕하세요 세계")["words"], 2)

    def test_apostrophe_and_hyphen_join(self):
        self.assertEqual(wordcount.count_text("don't well-known")["words"], 2)

    def test_empty(self):
        s = wordcount.count_text("")
        self.assertEqual((s["lines"], s["words"], s["chars"]), (0, 0, 0))


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, content, mode="w"):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
            f.write(content)
        return path

    def test_single_file(self):
        p = self.write("a.txt", "one two three\n")
        code, out, err = run(p)
        self.assertEqual(code, 0)
        self.assertIn("words=3", out)
        self.assertNotIn("total", out)

    def test_lines_and_chars(self):
        p = self.write("a.txt", "a b\nc\n")
        code, out, _ = run("-l", "-c", p)
        self.assertEqual(code, 0)
        self.assertIn("lines=2  words=3  chars=6", out)

    def test_multiple_files_total(self):
        a = self.write("a.txt", "a b\n")
        b = self.write("b.txt", "c d e\n")
        code, out, _ = run(a, b)
        self.assertEqual(code, 0)
        self.assertIn("words=5  total", out)

    def test_folder_recursive_skips_hidden(self):
        self.write("x.txt", "hello world\n")
        self.write("sub/y.md", "one two three\n")
        self.write(".hidden/z.txt", "skip me please\n")
        code, out, _ = run(self.dir)
        self.assertEqual(code, 0)
        self.assertIn("words=5  total", out)
        self.assertNotIn("z.txt", out)

    def test_binary_skipped(self):
        self.write("t.txt", "a b\n")
        self.write("bin.dat", b"\0\1\2", mode="wb")
        code, out, err = run(self.dir)
        self.assertEqual(code, 0)
        self.assertIn("바이너리", err)
        self.assertIn("words=2", out)

    def test_missing_file_friendly_error_exit_1(self):
        missing = os.path.join(self.dir, "nope.txt")
        code, out, err = run(missing)
        self.assertEqual(code, 1)
        self.assertIn("파일을 찾을 수 없습니다", err)
        self.assertIn("nope.txt", err)
        self.assertNotIn("Traceback", err)

    def test_missing_file_others_still_counted(self):
        a = self.write("a.txt", "a b\n")
        code, out, err = run(a, os.path.join(self.dir, "nope.txt"))
        self.assertEqual(code, 1)
        self.assertIn("words=2", out)
        self.assertIn("찾을 수 없습니다", err)

    def test_empty_folder_exit_1(self):
        code, _, err = run(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("셀 파일이 없습니다", err)

    def test_bad_encoding_exit_1(self):
        p = self.write("a.txt", "a\n")
        code, _, err = run("-e", "bogus", p)
        self.assertEqual(code, 1)
        self.assertIn("알 수 없는 인코딩", err)

    def test_stdin(self):
        code, out, _ = run(stdin="a b c d\n")
        self.assertEqual(code, 0)
        self.assertIn("words=4  <stdin>", out)

    def test_top_ignore_case(self):
        code, out, _ = run("-t", "1", "-i", stdin="A a B\n")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"\na\s+2\n")


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wordcount.py")


class ExitCodeTest(unittest.TestCase):
    """실제 프로세스로 실행해 종료 코드(returncode)와 오류 출력을 확인한다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args, stdin=""):
        import subprocess

        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_success_exit_0(self):
        path = os.path.join(self.dir, "a.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("a b c\n")
        r = self.cli(path)
        self.assertEqual(r.returncode, 0)
        self.assertIn("words=3", r.stdout)
        self.assertEqual(r.stderr, "")

    def test_missing_file_exit_1(self):
        r = self.cli(os.path.join(self.dir, "nope.txt"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("파일을 찾을 수 없습니다", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_empty_folder_exit_1(self):
        r = self.cli(self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("셀 파일이 없습니다", r.stderr)

    def test_bad_encoding_exit_1(self):
        path = os.path.join(self.dir, "a.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("a\n")
        r = self.cli("-e", "bogus", path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("알 수 없는 인코딩", r.stderr)

    def test_bad_option_exit_2(self):
        # argparse 사용법 오류는 관례대로 종료 코드 2
        r = self.cli("--no-such-option")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)


if __name__ == "__main__":
    unittest.main()
