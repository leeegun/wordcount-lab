#!/usr/bin/env python3
"""텍스트 파일의 단어 수를 세는 CLI.

사용 예:
    python wordcount.py <파일 또는 폴더>
    python wordcount.py file.txt
    python wordcount.py test            # 폴더 안의 모든 텍스트 파일 (하위 폴더 포함)
    python wordcount.py a.txt b.txt --lines --chars
    cat file.txt | python wordcount.py
    python wordcount.py file.txt --top 10
"""

import argparse
import os
import re
import sys
from collections import Counter

WORD_RE = re.compile(r"\w+(?:['’-]\w+)*", re.UNICODE)


def count_text(text: str) -> dict:
    words = WORD_RE.findall(text)
    return {
        "lines": len(text.splitlines()),
        "words": len(words),
        "chars": len(text),
        "_words": words,
    }


def read_source(path: str, encoding: str) -> str | None:
    """파일 내용을 읽는다. 바이너리 파일이면 None."""
    if path == "-":
        return sys.stdin.read()
    with open(path, "rb") as f:
        data = f.read()
    if b"\0" in data[:8192]:
        return None
    # 텍스트 모드 open()과 같게 줄바꿈(\r\n, \r)을 \n으로 통일
    return data.decode(encoding, errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def friendly_error(path: str, e: OSError) -> str:
    if isinstance(e, FileNotFoundError):
        return f"'{path}' 파일을 찾을 수 없습니다. 경로와 파일 이름을 확인해 주세요."
    if isinstance(e, PermissionError):
        return f"'{path}' 파일을 읽을 권한이 없습니다."
    if isinstance(e, IsADirectoryError):
        return f"'{path}'은(는) 폴더입니다."
    return f"'{path}' 파일을 읽지 못했습니다: {e.strerror or e}"


def expand_paths(paths: list[str]) -> list[str]:
    """폴더는 하위 파일 목록으로 펼친다 (숨김 폴더/파일 제외, 이름순)."""
    result = []
    for path in paths:
        if path != "-" and os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                result.extend(
                    os.path.join(root, f) for f in sorted(files) if not f.startswith(".")
                )
        else:
            result.append(path)
    return result


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="wordcount",
        description="텍스트 파일의 단어 수를 셉니다. 폴더를 주면 하위 파일까지 모두 셉니다. "
        "경로를 생략하거나 '-'를 주면 표준 입력을 읽습니다.",
    )
    p.add_argument("files", nargs="*", default=["-"], help="대상 파일 또는 폴더 (기본: 표준 입력)")
    p.add_argument("-l", "--lines", action="store_true", help="줄 수도 출력")
    p.add_argument("-c", "--chars", action="store_true", help="문자 수도 출력")
    p.add_argument("-t", "--top", type=int, metavar="N", help="가장 많이 나온 단어 N개 출력")
    p.add_argument("-i", "--ignore-case", action="store_true", help="--top 집계 시 대소문자 무시")
    p.add_argument("-e", "--encoding", default="utf-8", help="파일 인코딩 (기본: utf-8)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    total = {"lines": 0, "words": 0, "chars": 0}
    freq = Counter()
    exit_code = 0
    processed = 0

    paths = expand_paths(args.files)
    if not paths:
        print(f"wordcount: 오류: 폴더 안에 셀 파일이 없습니다: {', '.join(args.files)}", file=sys.stderr)
        return 1

    for path in paths:
        try:
            text = read_source(path, args.encoding)
        except OSError as e:
            print(f"wordcount: 오류: {friendly_error(path, e)}", file=sys.stderr)
            exit_code = 1
            continue
        except LookupError:
            print(f"wordcount: 오류: 알 수 없는 인코딩입니다: {args.encoding}", file=sys.stderr)
            return 1
        if text is None:
            print(f"wordcount: {path}: 바이너리 파일이라 건너뜀", file=sys.stderr)
            continue

        stats = count_text(text)
        processed += 1
        for k in total:
            total[k] += stats[k]
        if args.top:
            words = stats["_words"]
            if args.ignore_case:
                words = [w.lower() for w in words]
            freq.update(words)

        print(format_row(stats, args, "<stdin>" if path == "-" else path))

    if processed > 1:
        print(format_row(total, args, "total"))

    if args.top and freq:
        print()
        width = max(len(w) for w, _ in freq.most_common(args.top))
        for word, n in freq.most_common(args.top):
            print(f"{word:<{width}}  {n}")

    return exit_code


def format_row(stats: dict, args: argparse.Namespace, name: str) -> str:
    parts = []
    if args.lines:
        parts.append(f"lines={stats['lines']}")
    parts.append(f"words={stats['words']}")
    if args.chars:
        parts.append(f"chars={stats['chars']}")
    return f"{'  '.join(parts)}  {name}"


if __name__ == "__main__":
    sys.exit(main())
