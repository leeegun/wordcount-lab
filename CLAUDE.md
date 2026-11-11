# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`wordcount.py` is a single-file Python CLI that counts words (and optionally lines/chars) in text files, folders (recursive), or stdin. User-facing messages are in Korean.

**Constraint:** standard library only — no third-party packages, including for tests (`unittest`, not pytest).

## Commands

```bash
python wordcount.py <file-or-folder> [...]      # -l lines, -c chars, -t N top words, -i ignore case, -e encoding
python -m unittest discover -s test -v          # all tests
python -m unittest discover -s test -k test_missing_file   # tests matching a name
```

No build or lint step is configured.

## How it works

Flow in `main()`: `expand_paths()` turns folders into a sorted, recursive file list (skipping names starting with `.`) → `read_source()` reads each file → `count_text()` counts → `format_row()` prints one row per file, plus a `total` row when more than one file was counted, then the optional `--top` frequency list.

Things that aren't obvious from a quick read:
- `read_source()` reads **bytes** so it can detect binary files (a NUL byte in the first 8 KB → returns `None`, and the file is skipped with a notice). Because of that, it normalizes `\r\n`/`\r` to `\n` itself; removing this makes `chars` wrong on Windows.
- Words are matched by `WORD_RE` (`\w+` joined by `'`, `’`, or `-`), so Korean text counts and `don't`/`well-known` count as one word each. This intentionally differs from `wc -w`.
- `count_text()` returns a private `_words` list used only for `--top`.

## Exit codes and errors

These are covered by tests, so keep them stable:
- `0` = success; `1` = a path was missing/unreadable, the folder had no files, or the encoding was unknown; `2` = argparse usage error.
- A missing file doesn't stop processing: the remaining files are still counted, and the exit code is `1`.
- Errors go to stderr as `wordcount: 오류: ...` (built by `friendly_error()`), never as a traceback.

## Tests

`test/test_wordcount.py` adds the repo root to `sys.path` so it can import `wordcount` (there's no package/`__init__.py`). It has three groups: `CountTextTest` (pure counting), `CliTest` (calls `main()` in-process with stdout/stderr captured), and `ExitCodeTest` (runs the script in a subprocess with `PYTHONIOENCODING=utf-8` to check real return codes).

`test/` also holds sample text files, so `python wordcount.py test` counts the test source too.

## 규칙·컨벤션

- **시크릿**: API 키·토큰은 `.env`에만 둔다. 절대 커밋하지 않는다. 커밋 전에 `.env`가 `.gitignore`에 들어 있는지 확인한다.
- **커밋 메시지**: Conventional Commits 타입(`feat`/`fix`/`docs`/`refactor`/`test`/`chore`) 뒤 콜론, 그리고 한국어 요약 한 줄.
  예: `feat: 여러 파일 단어수 합계 출력`
- **테스트**: 로직을 바꾸면 테스트도 함께 고친다. 전체 테스트가 통과하지 않으면 커밋하지 않는다.
