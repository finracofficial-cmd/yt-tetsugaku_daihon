#!/usr/bin/env python3
"""参照台本92本から「話法辞典」を抽出する。

    python3 tools/extract_phrasebook.py > knowledge/reference-channel/phrasebook.md

60万字を執筆時に読むことはできない。そこで、実際に使われている言い回しを
用途別に集計・抜粋して、1万字ほどに圧縮する。頻度は全92本の実測である。

**抜粋文は自動音声認識に由来し、誤変換を含む。言い回しの型としてのみ使い、
数値・固有名詞をここから引用してはならない。**
"""

import collections
import glob
import os
import re
import sys

DIR = "knowledge/reference-scripts/auto"
NUM = re.compile(r"[0-9０-９]")


def load():
    out = []
    for p in sorted(glob.glob(os.path.join(DIR, "*.txt"))):
        lines = [l for l in open(p, encoding="utf-8").read().split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        title = lines[0]
        body = "".join(lines[2:])
        sents = [s.strip() for s in re.split(r"(?<=。)", body) if s.strip()]
        if len(sents) < 40:
            continue
        out.append((title, sents))
    return out


def clean(s, limit=100):
    s = s.strip()
    return s if len(s) <= limit else s[:limit] + "…"


def section(title, note=""):
    print(f"\n## {title}\n")
    if note:
        print(note + "\n")


def freq_table(counter, total, top=18, unit="回"):
    print("| 語 | 回数 | 1本あたり |")
    print("|---|---|---|")
    for k, v in counter.most_common(top):
        print(f"| {k} | {v}{unit} | {v/total:.1f} |")


def samples(sents_all, pattern, n=12, limit=95, exclude=None):
    rx = re.compile(pattern)
    seen, out = set(), []
    for s in sents_all:
        if not rx.search(s):
            continue
        if exclude and re.search(exclude, s):
            continue
        key = s[:14]
        if key in seen:
            continue
        seen.add(key)
        out.append(clean(s, limit))
        if len(out) >= n:
            break
    for s in out:
        print(f"> {s}")
        print()


def main():
    docs = load()
    n = len(docs)
    allsents = [s for _, ss in docs for s in ss]

    print("# 話法辞典 — 参照チャンネル92本の言い回し実測")
    print()
    print(f"全{n}本 / {len(allsents):,}文 / {sum(len(s) for s in allsents):,}字 から自動抽出した。")
    print("`python3 tools/extract_phrasebook.py > knowledge/reference-channel/phrasebook.md` で再生成する。")
    print()
    print("**この文書の使い方。** 執筆中、手が止まったらここを見る。"
          "構成と分量の正は `.claude/skills/daihon/references/beats.md`、"
          "文体の規律は `style.md` にある。ここにあるのは**語彙と言い回しだけ**である。")
    print()
    print("> **抜粋文は自動音声認識に由来し、誤変換を含む。** 言い回しの型としてのみ使い、"
          "**数値・固有名詞をここから引用してはならない。**")

    # ---- 1 文頭の接続
    conj = ["だが", "そして", "つまり", "ところが", "ここで", "ただし", "しかし", "一方",
            "それでも", "さらに", "例えば", "たとえば", "もちろん", "むしろ", "実は",
            "やがて", "とはいえ", "なぜなら", "ちなみに", "そもそも", "しかも", "だからこそ"]
    c = collections.Counter()
    for s in allsents:
        for k in conj:
            if s.startswith(k):
                c[k] += 1
                break
    section("1. 文頭の接続語",
            "段落と段落、文と文をつなぐ運動。**「だが」が突出して多い。**「しかし」より「だが」を選ぶのがこのチャンネルの癖である。")
    freq_table(c, n)

    # ---- 2 冒頭
    dstart = sum(1 for _, ss in docs if re.match(r"^[0-9０-９]", ss[0].lstrip()))
    dhas = sum(1 for _, ss in docs if NUM.search(ss[0]))
    section("2. 冒頭の第1文(全92本から抜粋)",
            f"型は「情景」「逆説」「二人称の問い」に割れる。**数字で始まる回は{dstart}本"
            f"({dstart/n*100:.0f}パーセント)、第1文に数字を含む回は{dhas}本"
            f"({dhas/n*100:.0f}パーセント)。** 統計から入る回も実在するので、"
            "数字を避ける必要はない。多数派が情景と逆説だというだけである。")
    heads = [ss[0] for _, ss in docs]
    kinds = {"情景": [], "逆説": [], "問い": [], "その他": []}
    for h in heads:
        if h.rstrip("。").endswith(("だろうか", "のか", "か")):
            kinds["問い"].append(h)
        elif re.search(r"ところが|のに|はずだ|しかし|だが|なぜか", h):
            kinds["逆説"].append(h)
        elif re.search(r"[時分]|夕方|夜|朝|駅|電車|部屋|窓|席|前に|いる。|座って|立って", h):
            kinds["情景"].append(h)
        else:
            kinds["その他"].append(h)
    for k, v in kinds.items():
        if not v:
            continue
        print(f"### {k}型({len(v)}本)")
        print()
        for h in v[:8]:
            print(f"> {clean(h, 90)}")
            print()

    # ---- 3 着地
    section("3. 着地の言い回し",
            "末尾の定型3文(登録・高評価・またお会いしましょう)を除いた、本編の最後の一文。")
    tails = []
    for _, ss in docs:
        for s in reversed(ss[-8:]):
            if any(k in s for k in ("登録", "高評価", "お会い", "考えすぎ", "ご視聴")):
                continue
            tails.append(s)
            break
    for t in tails[:16]:
        print(f"> {clean(t, 100)}")
        print()

    # ---- 4 想定反論
    section("4. 想定反論の代弁",
            "視聴者の反論を先に口に出す言い回し。**「〜かもしれない」で代弁し、「だが」で越える**のが基本形である。")
    samples(allsents, r"かもしれない|と思うだろう|待ってくれ|本当にそうだろうか|反論があるだろう", 12)

    section("5. 認めてから越える",
            "承認句。**参照の中央値は1件で、毎回は置かない。**")
    samples(allsents, r"その通り|指摘は|懸念は|もっともだ|否定しない|事実である", 8)

    # ---- 6 翻訳
    section("6. 現代語への翻訳",
            "抽象概念を、視聴者がすでに知っている具体物に対応させる。**参照の中央値は1箇所と少ない。"
            "本チャンネルは意図的にここを3箇所以上に増やす。**")
    samples(allsents, r"で言えば|に例え|にたとえ|ようなもの|に置き換え|に相当", 12)

    # ---- 7 限界
    section("7. 限界と反証",
            "**参照の中央値は0箇所。** 数が少ないので、使える言い回しはここに集めた実例がほぼ全部である。")
    samples(allsents, r"限界|再現され|追試|とは限らない|議論が続|確定していない|断定はできない", 10)

    # ---- 8 数字
    section("8. 数字の出し方",
            "数字を独立させ、直後の一文で意味づける。**丸めない。**")
    samples(allsents, r"[0-9０-９]+(パーセント|人|倍|種|件)", 12,
            exclude=r"^(だが|そして|つまり)")

    # ---- 9 二人称
    section("9. 二人称の呼びかけ",
            "確認・指示・同定の3種類。**参照の中央値は12回。**")
    samples(allsents, r"あなた|してみてほしい|想像して|考えてみて", 12)

    # ---- 10 巨視化
    section("10. 巨視化",
            "進化史・歴史・制度へ引き上げる。**参照の中央値は6箇所と多い。ここは参照の得意技である。**")
    samples(allsents, r"何万年|数万年|祖先|狩猟採集|人類は|種として|世紀|文明", 10)

    # ---- 11 語彙
    section("11. チャンネル固有の語彙",
            "全92本で頻出する名詞。**言い換えに迷ったらこの語を選ぶと声が揃う。**")
    words = collections.Counter()
    body = "".join(allsents)
    for w in re.findall(r"[一-龥]{2,4}", body):
        words[w] += 1
    stop = {"我々", "自分", "人間", "場合", "本当", "相手", "今日", "以上", "以下",
            "一つ", "二つ", "全て", "全く", "非常", "存在", "可能", "必要"}
    rows = [(w, v) for w, v in words.most_common(200) if w not in stop][:40]
    print("| 語 | 回数 | 語 | 回数 |")
    print("|---|---|---|---|")
    for i in range(0, 40, 2):
        a, b = rows[i], rows[i + 1]
        print(f"| {a[0]} | {a[1]} | {b[0]} | {b[1]} |")

    # ---- 12 文末
    section("12. 文末の形",
            "断定・推量・問いの配分。**「である」「だ」の静かな断定が土台で、そこに問いを差す。**")
    ends = collections.Counter()
    for s in allsents:
        t = s.rstrip("。")
        for k in ("のである", "である", "だろうか", "のだろう", "ではない", "かもしれない",
                  "のだ", "ている", "だった", "ない", "する", "た", "だ"):
            if t.endswith(k):
                ends[k] += 1
                break
    freq_table(ends, n, top=13)


if __name__ == "__main__":
    sys.exit(main())
