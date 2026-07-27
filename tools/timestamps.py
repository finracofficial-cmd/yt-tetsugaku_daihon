#!/usr/bin/env python3
"""概要欄のタイムスタンプを、台本の字数から算出する。

参照チャンネルの概要欄は Prologue / Chapter 1〜4 / Epilogue の6ブロックに
章題をつけている。41ビートをその6つに束ね、累積字数を読み上げ速度で割って
各ブロックの開始時刻を出す。

    python3 tools/timestamps.py output/<dir>/03_台本.txt
    python3 tools/timestamps.py output/<dir>/03_台本.txt --rate 340

読み上げ速度の既定値327字/分は、参照台本A〜Dのタイムスタンプから実測した値
(311〜340字/分)の平均。話者や編集の間の取り方で前後するため、**書き出した
動画の実尺で必ず補正すること。** このツールが出すのは初稿の目安である。
"""

import argparse
import os
import re
import sys

# 41ビートを概要欄の6ブロックへ束ねる。(章名, 開始ビート, 終了ビート)
CHAPTERS = [
    ("Prologue",  1,  6),   # ブロックA フック
    ("Chapter 1", 7,  13),  # ブロックB 通説の解体
    ("Chapter 2", 14, 20),  # ブロックC メカニズムの解剖
    ("Chapter 3", 21, 27),  # ブロックD 帳簿
    ("Chapter 4", 28, 36),  # ブロックE 文明史 + F 代償
    ("Epilogue",  37, 41),  # ブロックG 回収と鏡
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
    if n < 38:
        print(f"段落数が {n} しかない。先に tools/audit.py を通すこと", file=sys.stderr)
        return 1
    if n != 41:
        print(f"注意: 段落数が {n} で41でないため、ビート対応が近似になる\n", file=sys.stderr)

    counts = [body_len(p) for p in paras]
    total = sum(counts)

    print(f"総字数 {total:,}字 / 読み上げ速度 {args.rate:g}字/分 / 全体 約{total/args.rate:.1f}分\n")
    print("▼タイムスタンプ")

    cum = 0
    rows = []
    for name, first, last in CHAPTERS:
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
