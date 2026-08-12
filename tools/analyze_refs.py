#!/usr/bin/env python3
"""参照台本の構造を一括で実測する。

    python3 tools/analyze_refs.py knowledge/reference-scripts/auto
    python3 tools/analyze_refs.py knowledge/reference-scripts/auto --json out.json

入力は 1行目=タイトル / 2行目=URL / 空行 / 本文 の形のテキスト。
自動字幕には段落の区切りが無いため、測るのは文単位の指標だけである。
`tools/beats.json` の patterns と marker 群をそのまま使うので、
参照側と自作側をまったく同じ物差しで測れる。
"""

import argparse
import json
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "tools", "beats.json"), encoding="utf-8"))

STUDY = re.compile(SPEC["patterns"]["study"])
SCENE = re.compile(SPEC["patterns"]["scene"])
MACRO = re.compile(SPEC["patterns"]["macro"])
SECOND = re.compile(SPEC["patterns"]["second_person"])
TOKENS = re.compile(r"[一-龥]{2,4}|[ァ-ヴー]{3,}")

STOP = {"自分", "人間", "私たち", "我々", "とき", "こと", "もの", "場合", "本当",
        "相手", "今日", "世界", "問題", "理由", "意味", "状態", "以上", "以下"}


def load(path):
    lines = [l for l in open(path, encoding="utf-8").read().split("\n") if l.strip()]
    if not lines:
        return "", "", ""
    title = lines[0]
    url = lines[1] if len(lines) > 1 and lines[1].startswith("http") else ""
    body = "".join(lines[2:] if url else lines[1:])
    return title, url, body


def sentences(body):
    return [s.strip() for s in re.split(r"(?<=。)", body) if s.strip()]


def decile(i, n):
    return min(9, int(i / n * 10))


def profile(path):
    title, url, body = load(path)
    ss = sentences(body)
    n = len(ss)
    if n < 40:
        return None

    # 最初の実データ
    first = next((i for i, s in enumerate(ss) if STUDY.search(s)), None)

    # 研究文の最長連続
    run = best = 0
    for s in ss:
        run = run + 1 if STUDY.search(s) else 0
        best = max(best, run)

    # 研究のある十分位 / 情景のある十分位
    sd = {decile(i, n) for i, s in enumerate(ss) if STUDY.search(s)}
    cd = {decile(i, n) for i, s in enumerate(ss) if SCENE.search(s)}

    # 冒頭モチーフへの回帰。台本全体に散る語は目印にならないので落とす。
    head = "".join(ss[:6])
    df = {}
    for s in ss:
        for w in set(TOKENS.findall(s)):
            df[w] = df.get(w, 0) + 1
    motif = {w for w in TOKENS.findall(head) if w not in STOP and df.get(w, 0) <= n / 12}
    cb = None
    for i in range(int(n * 0.6), n):
        if len(set(TOKENS.findall(ss[i])) & motif) >= 2:
            cb = i / n
    # 末尾の定型(登録・高評価)を除いた本編の終わり
    body_end = n
    for i in range(n - 1, max(0, n - 8), -1):
        if "登録" in ss[i] or "高評価" in ss[i] or "また" in ss[i] and "動画" in ss[i]:
            body_end = i

    def count(markers):
        return sum(1 for s in ss if any(k in s for k in markers))

    reb = [i for i, s in enumerate(ss)
           if any(k in s for k in SPEC["rebuttal_openers"])]
    return {
        "file": os.path.basename(path),
        "title": title,
        "chars": len(body),
        "sents": n,
        "first_data": round(first / n, 3) if first is not None else None,
        "study_run_max": best,
        "study_deciles": len(sd),
        "study_free_deciles": 10 - len(sd),
        "scene_deciles": len(cd),
        "scene_open": 1 if cd & {0} else 0,
        "scene_mid": len(cd & set(range(2, 8))),
        "scene_close": 1 if cd & {8, 9} else 0,
        "callback": round(cb, 3) if cb is not None else None,
        "questions": sum(1 for s in ss if s.rstrip("。」").endswith(("か", "だろう"))),
        "second_person": len(SECOND.findall(body)),
        "you": body.count("あなた"),
        "rebuttals": len(reb),
        "rebuttal_late": sum(1 for i in reb if i / n >= 0.7),
        "concessions": count(SPEC["rebuttal_concessions"]),
        "analogies": sum(body.count(k) for k in SPEC["analogy_markers"]),
        "limitations": count(SPEC["limitation_markers"]),
        "macro": sum(1 for s in ss if MACRO.search(s)),
        "meta": count(SPEC["meta_markers"]),
        "sent_len_med": round(statistics.median(len(s) for s in ss), 1),
        "body_end": round(body_end / n, 3),
    }


NUMERIC = ["chars", "sents", "first_data", "study_run_max", "study_deciles",
           "study_free_deciles", "scene_mid", "callback", "questions",
           "second_person", "you", "rebuttals", "rebuttal_late", "concessions",
           "analogies", "limitations", "macro", "meta", "sent_len_med"]


def pct(vals, p):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json", help="全件の生データをJSONで書き出す")
    args = ap.parse_args()

    rows = []
    for fn in sorted(os.listdir(args.dir)):
        if not fn.endswith(".txt") or fn == "index.tsv":
            continue
        r = profile(os.path.join(args.dir, fn))
        if r:
            rows.append(r)

    if not rows:
        print("解析対象なし", file=sys.stderr)
        return 2

    print(f"解析 {len(rows)}本  ({args.dir})")
    print("=" * 78)
    print(f"{'指標':<20}{'最小':>9}{'p10':>9}{'中央':>9}{'p90':>9}{'最大':>9}")
    print("-" * 78)
    for k in NUMERIC:
        vals = [r[k] for r in rows if r.get(k) is not None]
        if not vals:
            continue
        print(f"{k:<20}{min(vals):>9}{pct(vals,0.1):>9}{pct(vals,0.5):>9}"
              f"{pct(vals,0.9):>9}{max(vals):>9}")
    print("-" * 78)
    miss = sum(1 for r in rows if r["callback"] is None)
    print(f"冒頭への回帰が検出できなかった本数: {miss}/{len(rows)}")
    print(f"研究ゼロの区間が0だった本数: {sum(1 for r in rows if r['study_free_deciles']==0)}/{len(rows)}")
    print(f"研究文が3文以上連続した本数: {sum(1 for r in rows if r['study_run_max']>=3)}/{len(rows)}")

    if args.json:
        json.dump(rows, open(args.json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\n書き出し: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
