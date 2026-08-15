#!/usr/bin/env python3
"""概要欄のタイムスタンプを、台本の字数から算出する。

参照チャンネルの概要欄は Prologue / Chapter 1〜4 / Epilogue の6ブロックに
章題をつけている。41ビートをその6つに束ね、累積字数を読み上げ速度で割って
各ブロックの開始時刻を出す。

    python3 tools/timestamps.py output/<dir>/03_台本.txt
    python3 tools/timestamps.py output/<dir>/03_台本.txt --rate 340

読み上げ速度の既定値327字/分は、参照台本8本(A〜Dと reference-scripts/viral の
4本)のタイムスタンプから実測した値(305〜349字/分)の平均。話者や編集の間の取り方で前後するため、**書き出した
動画の実尺で必ず補正すること。** このツールが出すのは初稿の目安である。
"""

import argparse
import os
import re
import sys

# 40段落を概要欄の6ブロックへ束ねる。(章名, 開始段落, 終了段落)
# v4.0の三層に対応する。Prologue=開幕、Chapter 1〜4=展開部を4等分、Epilogue=着地。
CHAPTERS = [
    ("Prologue",  1,  5),   # 開幕
    ("Chapter 1", 6,  12),  # 展開 1
    ("Chapter 2", 13, 19),  # 展開 2
    ("Chapter 3", 20, 26),  # 展開 3
    ("Chapter 4", 27, 33),  # 展開 4
    ("Epilogue",  34, 41),  # 着地
]

DEFAULT_RATE = 327.0  # 字/分


def body_len(text):
    return len(re.sub(r"\s", "", text))


def main():
    ap = argparse.ArgumentParser(description="概要欄のタイムスタンプを算出する")
    ap.add_argument("path", help="台本本文のプレーンテキスト")
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE,
                    help=f"読み上げ速度(字/分)。既定 {DEFAULT_RATE:g}")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"ファイルが見つからない: {args.path}", file=sys.stderr)
        return 2

    with open(args.path, encoding="utf-8") as f:
        paras = [p.strip() for p in re.split(r"\n\s*\n", f.read()) if p.strip()]

    n = len(paras)
    if n < 36:
        print(f"段落数が {n} しかない。先に tools/audit.py を通すこと", file=sys.stderr)
        return 1
    if n != 40:
        print(f"注意: 段落数が {n} なので、章の区切りを40段落基準から比例で割り付ける\n",
              file=sys.stderr)

    counts = [body_len(p) for p in paras]
    total = sum(counts)

    print(f"総字数 {total:,}字 / 読み上げ速度 {args.rate:g}字/分 / 全体 約{total/args.rate:.1f}分\n")
    print("▼タイムスタンプ")

    cum = 0
    rows = []
    # 40段落基準の区切りを、実際の段落数へ比例させる(tools/audit.py と同じ考え方)
    def scale(i):
        return max(1, min(n, round(i * n / 40)))

    for name, first, last in CHAPTERS:
        first, last = scale(first), (n if name == CHAPTERS[-1][0] else scale(last))
        start_sec = cum / args.rate * 60
        chars = sum(counts[i] for i in range(first - 1, min(last, n)))
        cum += chars
        rows.append((name, start_sec, chars))
        print(f"{int(start_sec)//60:02d}:{int(start_sec)%60:02d} - {name}:")

    print("\n各ブロックの内訳")
    print("-" * 46)
    for name, start_sec, chars in rows:
        print(f"  {name:<10} {chars:>5}字  約{chars/args.rate:4.1f}分")
    print("-" * 46)
    print("\n章題は手で付ける。内容の説明ではなく短い詩句にすること。")
    print("時刻は初稿の目安。書き出した動画の実尺で必ず補正すること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
