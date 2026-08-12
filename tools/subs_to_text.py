#!/usr/bin/env python3
"""YouTube自動字幕(json3)を、解析用のプレーンテキストへ変換する。

    python3 tools/subs_to_text.py knowledge/reference-scripts/auto

同じディレクトリの <videoId>.ja-orig.json3 を読み、<videoId>.txt を書く。
1行目にタイトル、2行目にURL、空行、以降が本文。knowledge/reference-scripts/viral/
の手作業版と同じ形にそろえてあるので、既存の解析スクリプトがそのまま動く。

注意:これは自動音声認識であり、誤変換を含む。構造と話法の参照にのみ使い、
数値・固有名詞をここから引用してはならない。
"""

import json
import os
import re
import sys

NOISE = re.compile(r"\[(音楽|拍手|笑|拍手と歓声|軽快な音楽|BGM)\]")


def convert(path):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for e in d.get("events", []):
        if e.get("aAppend"):
            continue
        for s in e.get("segs", []):
            out.append(s.get("utf8", ""))
    t = "".join(out)
    t = NOISE.sub("", t)
    t = t.replace("\n", "")
    # ASRの「?」「!」は句点にそろえる。解析側の文分割は「。」で行うため。
    t = t.replace("?", "。").replace("？", "。").replace("!", "。").replace("！", "。")
    t = re.sub(r"。{2,}", "。", t)
    t = re.sub(r"\s+", "", t)
    return t.strip()


def main(dirpath):
    index = {}
    idx_path = os.path.join(dirpath, "index.tsv")
    if os.path.exists(idx_path):
        for line in open(idx_path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if parts and parts[0]:
                index[parts[0]] = parts[1] if len(parts) > 1 else ""

    n = 0
    for fn in sorted(os.listdir(dirpath)):
        if not fn.endswith(".ja-orig.json3"):
            continue
        vid = fn.split(".")[0]
        body = convert(os.path.join(dirpath, fn))
        if len(body) < 500:
            print(f"skip(短すぎ) {vid} {len(body)}字")
            continue
        head = f"{index.get(vid, vid)}\nhttps://www.youtube.com/watch?v={vid}\n\n"
        with open(os.path.join(dirpath, vid + ".txt"), "w", encoding="utf-8") as f:
            f.write(head + body + "\n")
        n += 1
    print(f"変換 {n}本")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "knowledge/reference-scripts/auto")
