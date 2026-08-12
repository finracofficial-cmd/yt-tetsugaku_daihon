#!/usr/bin/env python3
"""参照チャンネルのタイトル・テーマ・学問タグを再生数と突き合わせる。

    python3 tools/analyze_titles.py
    python3 tools/analyze_titles.py --perm 20000

入力は knowledge/reference-scripts/auto/ の index.tsv(id と タイトル)と
views.txt(id|再生数|尺)。どちらも yt-dlp で取得したものである。

出力の解釈は knowledge/reference-channel/titles.md に書いてある。
**個別の検定はいずれも検定数で補正すれば残らない。テーマが効き構造は効かない、
という大きな方向だけを読むこと。**
"""

import argparse
import os
import random
import re
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "knowledge", "reference-scripts", "auto")

# テーマ区分。上から順に当たったものを採用する排他割り当て。
TOPICS = [
    ("恋愛と性", r"モテ|恋愛|好き|惚|デート|婚活|結婚|浮気|失恋|告白|彼氏|彼女|異性|"
                 r"オス性|性欲|セックス|美人|イケメン|ネット恋愛|ラブレター"),
    ("金と地位", r"年収|価値|市場|投資|貧|富|格差|階級|港区|夜職|ブランド|高級|課金|奢|金"),
    ("容姿と身体", r"容姿|顔|見た目|背|太|痩|体|身体|老け|ハゲ|筋肉|頭がデカ"),
    ("仕事と能力", r"仕事|会社|上司|職|働|無能|有能|学歴|勉強|才能|センス|知能|賢|努力|忙しい"),
    ("人間関係", r"友人|友達|孤独|人間関係|集団|群れ|嫌|悪口|嫉妬|マウント|いじめ|陰口|"
                 r"承認|他人|悪役|正義の味方|英雄|悪人"),
    ("心と脳", r"脳|不安|恐怖|幸福|幸せ|快感|依存|中毒|怒|悲|感情|記憶|後悔|罪悪|眠|睡眠|痛|共感"),
    ("社会と制度", r"社会|国家|都市|東京|地方|人口|少子|政治|宗教|文化|歴史|制度|法|子を残"),
    ("モノと現象", r"音楽|音|色|匂|味|食|うんこ|物|道具|言語|言葉|生物|動物|進化"),
]


def load():
    titles = {}
    p = os.path.join(DIR, "index.tsv")
    for line in open(p, encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if len(c) >= 2:
            titles[c[0]] = c[1]
    rows = []
    p = os.path.join(DIR, "views.txt")
    for age, line in enumerate(open(p, encoding="utf-8")):
        c = line.strip().split("|")
        if len(c) == 3 and c[1].isdigit():
            t = titles.get(c[0], "")
            core = re.sub(r"【[^】]*】", "", t).replace("｜", "").strip()
            tags = re.findall(r"【([^】]*)】", t)
            tag = tags[0] if tags else (t.split("｜")[-1] if "｜" in t else "")
            rows.append({
                "id": c[0], "t": t, "core": core, "v": int(c[1]),
                "dur": int(c[2]) if c[2].isdigit() else 0, "age": age,
                "tags": [x for x in re.split(r"[×xX]", tag) if x] if tag else [],
            })
    for r in rows:
        r["ntag"] = len(r["tags"])
        r["len"] = len(r["t"])
        r["corelen"] = len(r["core"])
        r["q"] = 1 if re.search(r"[？?]", r["t"]) else 0
        r["comma"] = 1 if "、" in r["core"] else 0
        r["quote"] = 1 if re.search(r"[「」“”\"]", r["core"]) else 0
        r["topic"] = "その他・混合"
        for name, rx in TOPICS:
            if re.search(rx, r["core"]):
                r["topic"] = name
                break
    return rows


# --- 統計(scipy が無い環境なので自前で持つ) ---

def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    out = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    na = sum((x - ma) ** 2 for x in a) ** .5
    nb = sum((y - mb) ** 2 for y in b) ** .5
    if not na or not nb:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (na * nb)


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def partial(a, b, c):
    ra, rb, rc = ranks(a), ranks(b), ranks(c)
    ab, ac, bc = pearson(ra, rb), pearson(ra, rc), pearson(rb, rc)
    d = ((1 - ac ** 2) * (1 - bc ** 2)) ** .5
    return (ab - ac * bc) / d if d else 0.0


def perm_rho(a, b, obs, n):
    bb = list(b)
    hit = 0
    for _ in range(n):
        random.shuffle(bb)
        if abs(spearman(a, bb)) >= abs(obs):
            hit += 1
    return (hit + 1) / (n + 1)


def perm_median(a, b, n):
    obs = st.median(a) - st.median(b)
    pool = a + b
    hit = 0
    for _ in range(n):
        random.shuffle(pool)
        if abs(st.median(pool[:len(a)]) - st.median(pool[len(a):])) >= abs(obs):
            hit += 1
    return obs, (hit + 1) / (n + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perm", type=int, default=10000, help="並べ替え検定の反復数")
    ap.add_argument("--seed", type=int, default=20260812)
    args = ap.parse_args()
    random.seed(args.seed)

    R = load()
    n = len(R)
    V = [r["v"] for r in R]
    A = [r["age"] for r in R]
    print(f"n={n}  再生 中央値{st.median(V):,.0f}(範囲 {min(V):,}〜{max(V):,})")
    print(f"新しさ順位との相関 rho={spearman(V, A):+.3f}  ← 古い動画ほど再生が多い交絡")

    print("\n" + "=" * 74)
    print("1. テーマの区分(排他割り当て)")
    print("=" * 74)
    g = defaultdict(list)
    for r in R:
        g[r["topic"]].append(r)
    for k, v in sorted(g.items(), key=lambda kv: -st.median([x["v"] for x in kv[1]])):
        vs = [x["v"] for x in v]
        top = max(v, key=lambda x: x["v"])
        print(f"  {k:<8}{len(v):>4}本  中央値{st.median(vs):>9,.0f}  平均{st.mean(vs):>9,.0f}"
              f"   {top['core'][:30]}")
    hi = [x["v"] for k in ("恋愛と性", "金と地位", "社会と制度") for x in g[k]]
    lo = [x["v"] for k in ("モノと現象", "心と脳") for x in g[k]]
    if hi and lo:
        d, p = perm_median(hi, lo, args.perm)
        print(f"\n  上位3区分({len(hi)}本)中央値{st.median(hi):,.0f} 対 "
              f"下位2区分({len(lo)}本)中央値{st.median(lo):,.0f}")
        print(f"  倍率{st.median(hi)/st.median(lo):.2f}倍  p={p:.4f}")

    print("\n" + "=" * 74)
    print("2. 学問タグ")
    print("=" * 74)
    for k in (0, 1, 2, 3):
        vs = [r["v"] for r in R if r["ntag"] == k]
        if vs:
            print(f"  タグ{k}個 {len(vs):>3}本  中央値{st.median(vs):>9,.0f}  平均{st.mean(vs):>9,.0f}")
    nt = [r["ntag"] for r in R]
    rho = spearman(nt, V)
    print(f"  個数と再生 rho={rho:+.3f}  p={perm_rho(nt, V, rho, args.perm):.4f}"
          f"  新しさ統制後={partial(nt, V, A):+.3f}")
    byt = defaultdict(list)
    for r in R:
        for t in r["tags"]:
            byt[t].append(r["v"])
    print()
    for t, vs in sorted(byt.items(), key=lambda kv: -st.median(kv[1])):
        if len(vs) >= 3:
            print(f"  {t:<14}{len(vs):>4}本  中央値{st.median(vs):>9,.0f}")
    a = [r["v"] for r in R if "進化心理学" in r["t"]]
    b = [r["v"] for r in R if "進化生物学" in r["t"]]
    if a and b:
        d, p = perm_median(a, b, args.perm)
        print(f"\n  進化心理学{len(a)}本 対 進化生物学{len(b)}本  "
              f"倍率{st.median(a)/st.median(b):.2f}倍  p={p:.4f}")

    print("\n" + "=" * 74)
    print("3. タイトルの書式")
    print("=" * 74)
    for key, lab in [("len", "タグ込み字数"), ("corelen", "タグ除き字数"), ("dur", "尺(秒)")]:
        a = [r[key] for r in R]
        rho = spearman(a, V)
        print(f"  {lab:<12} 中央値{st.median(a):>6.0f}  rho={rho:+.3f}"
              f"  p={perm_rho(a, V, rho, args.perm):.4f}  統制後={partial(a, V, A):+.3f}")
    for key, lab in [("comma", "読点「、」"), ("q", "疑問符「？」"), ("quote", "引用符")]:
        yes = [r["v"] for r in R if r[key]]
        no = [r["v"] for r in R if not r[key]]
        if yes and no:
            _, p = perm_median(yes, no, args.perm)
            print(f"  {lab:<12} あり{len(yes):>3}本 中央値{st.median(yes):>8,.0f} / "
                  f"なし{len(no):>3}本 {st.median(no):>8,.0f}  "
                  f"倍率{st.median(yes)/st.median(no):.2f}  p={p:.4f}")

    print("\n" + "=" * 74)
    print("4. 上位1/4と下位1/4のタイトル")
    print("=" * 74)
    S = sorted(R, key=lambda r: -r["v"])
    k = len(S) // 4
    print("  【上位】")
    for r in S[:10]:
        print(f"    {r['v']:>7,}  {r['core'][:44]}")
    print("  【下位】")
    for r in S[-10:]:
        print(f"    {r['v']:>7,}  {r['core'][:44]}")

    print("\n※ 個別の検定は検定数で補正すれば残らない。"
          "テーマが効き構造は効かない、という方向だけを読むこと。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
