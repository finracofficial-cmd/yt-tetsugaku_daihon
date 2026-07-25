#!/usr/bin/env python3
"""audit.py の自己テスト。

仕様を満たす合成台本を組み立てて合格することと、
欠陥を入れた台本が正しく不合格になることを確認する。

    python3 tools/test_audit.py
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "tools", "audit.py")
SPEC = json.load(open(os.path.join(ROOT, "tools", "beats.json"), encoding="utf-8"))

FILLER = "この構造は静かに人の判断を書き換えている。"


def make_paragraph(target, tail):
    """目標字数を満たす段落を作る。tail で末尾を指定する。"""
    body = ""
    while len(body) + len(tail) < target:
        body += FILLER
    return body + tail


def build_script(spec, break_beat=None):
    paras = []
    q_ends = set(spec["question_end_beats"])
    for b in spec["beats"]:
        n, t = b["n"], b["target"]
        if break_beat and n == break_beat:
            paras.append("短い。")
            continue
        if n == 3:
            tail = "市場規模は1781万円、件数は4万8230件、人数は115万人である。"
        elif n in q_ends:
            tail = "では、その先には何が起きているのだろうか。"
        elif n == 11:
            tail = "想像してみて欲しい。あなたの手元にも同じ数字が並んでいる。"
        elif n in (19, 27, 35):
            tail = "考えてみて欲しい。"
        elif n == 41:
            tail = spec["signature"] + "よろしければチャンネル登録と高評価をお願いします。それでは次の動画で、またお会いしましょう。"
        else:
            tail = "そこに値札がついている。"
        paras.append(make_paragraph(t, tail))
    return "\n\n".join(paras)


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        p = subprocess.run([sys.executable, AUDIT, path], capture_output=True, text=True)
        return p.returncode, p.stdout
    finally:
        os.unlink(path)


def main():
    failures = []

    code, out = run(build_script(SPEC))
    if code != 0:
        failures.append("仕様準拠の台本が不合格になった")
        print(out)

    code, out = run(build_script(SPEC, break_beat=30))
    if code == 0:
        failures.append("ビート30を潰した台本が合格してしまった")

    code, out = run(build_script(SPEC).replace("そこに値札がついている。", "そこに値札がついている【重要】。", 1))
    if code == 0:
        failures.append("禁止記号を含む台本が合格してしまった")

    code, out = run(build_script(SPEC).replace(SPEC["signature"], "おわり。"))
    if code == 0:
        failures.append("シグネチャの無い台本が合格してしまった")

    if failures:
        for f in failures:
            print(f"NG: {f}")
        return 1
    print("OK: audit.py は仕様準拠を合格、欠陥3種を不合格と判定した")
    return 0


if __name__ == "__main__":
    sys.exit(main())
