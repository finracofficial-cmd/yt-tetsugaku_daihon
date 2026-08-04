#!/usr/bin/env python3
"""台本の機械監査(工程4・第1段階)

使い方:
    python3 tools/audit.py output/<dir>/03_台本.txt
    python3 tools/audit.py output/<dir>/03_台本.txt --verbose

入力は本文のみのプレーンテキスト。段落は空行で区切る。
FAILが1つでもあれば終了コード1を返す。
"""

import argparse
import json
import os
import re
import sys
import unicodedata

SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beats.json")

KATAKANA = r"[ァ-ヴーｦ-ﾟ]"

RESULTS = []


def record(level, label, detail=""):
    RESULTS.append((level, label, detail))


def body_len(text):
    """空白・改行を除いた文字数。"""
    return len(re.sub(r"\s", "", text))


def load_paragraphs(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    raw = unicodedata.normalize("NFC", raw)
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    return paras


def map_beats(paras, spec):
    """段落をビート番号に対応づける。(beat_no, text) のリストを返す。"""
    beats = spec["beats"]
    n = len(paras)
    if n == len(beats):
        return list(zip([b["n"] for b in beats], paras)), True
    if n == len(beats) - 1:
        # ビート40(メタCTA)は省略可
        nums = [b["n"] for b in beats if b["n"] != 40]
        return list(zip(nums, paras)), True
    nums = [b["n"] for b in beats][:n]
    if n > len(beats):
        nums += list(range(len(beats) + 1, n + 1))
    return list(zip(nums, paras)), False


def strip_quotes(text):
    """かぎ括弧内の引用を除去(敬語・煽り語の誤検出を避けるため)。"""
    return re.sub(r"「[^」]*」", "", text)


def check_length(paras, spec):
    total = sum(body_len(p) for p in paras)
    lo = spec["body_min"]
    if total >= lo:
        record("PASS", f"本文の総字数 {total:,}字", f"下限{lo:,}字")
    else:
        record("FAIL", f"本文の総字数 {total:,}字", f"下限{lo:,}字に{lo - total:,}字不足。増築が必要")
    if total > spec["body_max_soft"]:
        record("WARN", f"総字数が目安上限を超過 {total:,}字", f"目安上限{spec['body_max_soft']:,}字。約20分を超える可能性")
    return total


def check_paragraphs(paras, spec, exact):
    n = len(paras)
    target = spec["paragraph_target"]
    hi = spec.get("paragraph_max", target)
    if n == target:
        record("PASS", f"段落数 {n}", f"目標{target}(ビート40のメタCTAは原則省略)")
    elif n == hi:
        record("PASS", f"段落数 {n}", "ビート40(メタCTA)を使う構成")
    elif n >= spec["paragraph_min"]:
        record("WARN", f"段落数 {n}", f"目標{target}。ビート対応が近似になる")
    else:
        record("FAIL", f"段落数 {n}", f"下限{spec['paragraph_min']}未満。ビートの欠落がある")
    if not exact:
        record("WARN", "ビート対応は近似", f"段落数が{target}でも{hi}でもないため、以下のビート別判定は参考値")


def check_beat_lengths(mapped, spec):
    by_n = {b["n"]: b for b in spec["beats"]}
    ratio_min = spec["beat_ratio_min"]
    short = []
    for n, text in mapped:
        b = by_n.get(n)
        if not b:
            continue
        actual = body_len(text)
        need = int(b["target"] * ratio_min)
        if actual < need:
            short.append((n, b["name"], actual, b["target"]))
    if short:
        detail = " / ".join(f"B{n} {name} {a}字(目標{t})" for n, name, a, t in short)
        record("FAIL", f"目標字数を{int(ratio_min*100)}パーセント下回るビート {len(short)}件", detail)
    else:
        record("PASS", "全ビートが目標字数を満たす", f"許容 目標の{int(ratio_min*100)}パーセント以上")


def check_heavy_beats(mapped, spec):
    by_n = {b["n"]: b for b in spec["beats"]}
    lo = spec["heavy_beat_min"]
    bad = []
    for n in spec["heavy_beats"]:
        text = dict(mapped).get(n)
        if text is None:
            bad.append(f"B{n} 欠落")
            continue
        a = body_len(text)
        if a < lo:
            bad.append(f"B{n} {by_n[n]['name']} {a}字")
    if bad:
        record("FAIL", f"重量級ビートが{lo}字未満", " / ".join(bad) + " ← ここが台本の格を決める。最優先で増築")
    else:
        record("PASS", "重量級ビート10・17・24・30・37", f"全て{lo}字以上")


def check_question_ends(mapped, spec):
    d = dict(mapped)
    bad = []
    for n in spec["question_end_beats"]:
        text = d.get(n)
        if text is None:
            bad.append(f"B{n} 欠落")
            continue
        tail = text.rstrip().rstrip("。」")
        if not tail.endswith("か"):
            bad.append(f"B{n} 末尾「{text.rstrip()[-14:]}」")
    if bad:
        record("FAIL", "ブロック末尾が疑問文で終わっていない", " / ".join(bad))
    else:
        record("PASS", "ブロック末尾13・20・27・32・36", "全て疑問文で終わる")


def check_twist_position(mapped, spec, total):
    n_twist = spec["twist_beat"]
    cum = 0
    found = False
    for n, text in mapped:
        cum += body_len(text)
        if n == n_twist:
            found = True
            break
    if not found:
        record("FAIL", "裏切り予告(ビート13)が見つからない", "")
        return
    ratio = cum / total if total else 0
    lo, hi = spec["twist_position_min"], spec["twist_position_max"]
    label = f"裏切り予告の位置 {ratio*100:.1f}パーセント地点"
    if lo <= ratio <= hi:
        record("PASS", label, f"許容{lo*100:.0f}〜{hi*100:.0f}パーセント")
    else:
        record("WARN", label, f"許容{lo*100:.0f}〜{hi*100:.0f}パーセントから外れている")


def check_tts(paras, spec):
    tts = spec["tts"]
    joined = "\n".join(paras)

    hits = sorted({c for c in tts["forbidden_chars"] + tts["forbidden_colons"] if c in joined})
    if hits:
        record("FAIL", "禁止記号を検出", " ".join(hits) + " ← AI音声が誤読または沈黙する")
    else:
        record("PASS", "禁止記号なし", "")

    # 中黒:カタカナ名の区切り以外は禁止
    bad_dots = []
    for m in re.finditer("・", joined):
        i = m.start()
        prev = joined[i - 1] if i > 0 else ""
        nxt = joined[i + 1] if i + 1 < len(joined) else ""
        if not (re.match(KATAKANA, prev or " ") and re.match(KATAKANA, nxt or " ")):
            bad_dots.append(joined[max(0, i - 8):i + 8].replace("\n", ""))
    if bad_dots:
        record("FAIL", f"列挙用の中黒を検出 {len(bad_dots)}件", " / ".join(bad_dots[:5]) + " ← 外国人名の区切りのみ許可")
    else:
        record("PASS", "中黒の用法", "外国人名の区切りのみ")

    allowed = set(tts["allowed_abbreviations"])
    latin = {w for w in re.findall(r"[A-Za-zＡ-Ｚａ-ｚ]{1,}", joined)}
    latin = {w for w in latin if w.upper() not in allowed}
    if latin:
        record("FAIL", f"カタカナ化されていない英字 {len(latin)}件", " ".join(sorted(latin)[:12]) + " ← ティンダー等のカタカナ表記に直す")
    else:
        record("PASS", "英字のカタカナ化", "定着略称のみ残存")

    if re.search(r"\d+\s*[%％]", joined):
        record("FAIL", "パーセント記号を検出", "「パーセント」と書く")


def check_style(mapped, spec):
    tts = spec["tts"]
    allowed = set(spec["polite_allowed_beats"])

    polite = []
    for n, text in mapped:
        if n in allowed:
            continue
        t = strip_quotes(text)
        # 「目を覚ます」「湯を冷ます」など、丁寧語ではない動詞の誤検出を除く
        t = re.sub(r"(覚|冷|励|澄|済|醒|欺|研)ます", "", t)
        if re.search(r"(です|ます|ください|ましょう)[。、]", t):
            polite.append(f"B{n}")
    if polite:
        record("WARN", f"本文に敬語 {len(polite)}件", " ".join(polite) + " ← 敬語はビート40〜41のみ。引用文中なら問題なし")
    else:
        record("PASS", "敬語の位置", "ビート40〜41のみ")

    joined = strip_quotes("\n".join(t for _, t in mapped))
    hype = [w for w in tts["hype_words"] if w in joined]
    if hype:
        record("WARN", "煽り語を検出", " ".join(hype) + " ← 静かに断定する文体に直す")
    else:
        record("PASS", "煽り語なし", "")


def check_engagement(mapped, spec):
    """引き込みの3装置。高再生台本4本を貫いていた技法で、欠けると正確でも面白くない。"""
    eng = spec.get("engagement")
    if not eng:
        return
    d = dict(mapped)
    joined = "\n".join(t for _, t in mapped)

    # 1 二人称
    lo = eng["second_person_min"]
    n_2p = len(re.findall(eng["second_person_pattern"], joined))
    if n_2p >= lo:
        record("PASS", f"二人称の呼びかけ {n_2p}回", f"下限{lo}回(参照4本は11・15・10・12回)")
    else:
        record("FAIL", f"二人称の呼びかけ {n_2p}回",
               f"下限{lo}回に{lo - n_2p}回不足。情景と問いかけを二人称で書き直す")
    good = eng["second_person_you_good"]
    n_you = len(re.findall(eng["second_person_you_pattern"], joined))
    if n_you < good:
        record("WARN", f"「あなた」自体は {n_you}回",
               f"目安{good}回。参照4本のうち最上位の1本は「我々」中心で2回だったため、文体上の選択であって誤りではない")

    # 2 想定反論 → 一部承認 → 反転
    lo = eng["rebuttal_min"]
    # 代弁+反転で成立とする。承認句は必須ではない(参照4本は反論のたびに承認を置かない)
    turns = eng.get("rebuttal_turns", ["だが", "ところが", "しかし"])
    hits = []
    for n, text in mapped:
        opened = any(k in text for k in eng["rebuttal_openers"])
        turned = any(k in text for k in turns) or any(k in text for k in eng["rebuttal_concessions"])
        if opened and turned:
            hits.append(n)
    if len(hits) >= lo:
        record("PASS", f"想定反論の往復 {len(hits)}回", "B" + " B".join(str(n) for n in hits))
    else:
        record("FAIL", f"想定反論の往復 {len(hits)}回",
               f"下限{lo}回。視聴者の反論を先に代弁し、一度認めてから越える段落が足りない")
    for n in eng["rebuttal_beats"]:
        if n not in hits and n in d:
            record("WARN", f"ビート{n}に想定反論の形がない", "「〜と思うかもしれない」と「だが」の組が無い")

    # 3 現代語への翻訳
    lo, good = eng["analogy_min"], eng["analogy_good"]
    n_ana = sum(joined.count(k) for k in eng["analogy_markers"])
    if n_ana >= good:
        record("PASS", f"現代語への翻訳 {n_ana}箇所", f"目安{good}箇所以上")
    elif n_ana >= lo:
        record("WARN", f"現代語への翻訳 {n_ana}箇所",
               f"下限{lo}は満たすが目安は{good}箇所。参照4本は3・6・1・5箇所")
    else:
        record("FAIL", f"現代語への翻訳 {n_ana}箇所",
               f"下限{lo}箇所。研究や概念を出したら、その場で視聴者の日常の具体物に対応させる")

    # 限界と反証。参照4本のうち明示していたのは1本のみのため、機械監査ではWARNに留める。
    # ただし本チャンネルの絶対規律から、ビート16は自前の規律として必須扱いを維持する。
    b = d.get(eng["limitation_beat"], "")
    if any(k in b for k in eng["limitation_markers"]):
        record("PASS", f"ビート{eng['limitation_beat']} 限界と反証", "追試・境界条件への言及あり")
    else:
        record("WARN", f"ビート{eng['limitation_beat']} に限界と反証がない",
               "自分が出した研究の限界を自分で言う。参照4本中1本のみの技法だが、本チャンネルでは必須扱い")

    # 予告リスト
    b = d.get(eng["preview_beat"], "")
    n_pre = sum(1 for k in eng["preview_markers"] if k in b)
    if n_pre >= 2:
        record("PASS", f"ビート{eng['preview_beat']} 意外な予告リスト", "列挙の形あり")
    else:
        record("WARN", f"ビート{eng['preview_beat']} に予告リストの形がない",
               "「この話には3つの意外な続きがある。ひとつ〜。ふたつ〜。そして3つ目〜」")


def check_meta(mapped, spec):
    """設計図を音読する言い回しの検出。参照4本は本編でこれをやらない。"""
    eng = spec.get("engagement") or {}
    if "meta_markers" not in eng:
        return
    allowed = set(eng.get("meta_allowed_beats", []))
    hits = []
    for n, text in mapped:
        if n in allowed:
            continue
        for k in eng["meta_markers"]:
            if k in text:
                hits.append(f"B{n}「{k}」")
    lo = eng.get("meta_max_outside", 2)
    if len(hits) <= lo:
        record("PASS", f"メタ発話 {len(hits)}件", f"許容{lo}件(参照4本は本編でほぼ使わない)")
    else:
        record("FAIL", f"メタ発話が多すぎる {len(hits)}件",
               " ".join(hits[:8]) + f" ← 許容{lo}件。設計図を音読せず、内容で転換する")

    # 承認句の過剰(参照は反論3回に対し承認1回程度)
    cmax = eng.get("concession_max")
    if cmax:
        # 地の文の「確かに」「正しい」は装置ではない。反論の代弁を含む段落だけを数える
        c = sum(1 for _, t in mapped
                if any(k in t for k in eng["rebuttal_openers"])
                and any(k in t for k in eng["rebuttal_concessions"]))
        if c > cmax:
            record("WARN", f"承認句のある段落 {c}件",
                   f"目安{cmax}件。毎回«その指摘は正しい»を置くと定型に見える")

    # 一文が長すぎないか
    smax = eng.get("sentence_max")
    if smax:
        longest = 0
        for _, t in mapped:
            for s in re.split(r"(?<=。)", t):
                longest = max(longest, body_len(s))
        if longest > smax:
            record("WARN", f"最長の一文 {longest}字", f"目安{smax}字以内")


def check_ending(mapped, spec):
    """ビート39で視聴者を断罪していないか(目視の補助)。"""
    text = dict(mapped).get(39, "")
    if not text:
        return
    accusing = [w for w in ("あなたもまた", "あなたも例外ではない", "あなた自身が", "あなたのその") if w in text]
    if accusing:
        record("WARN", "ビート39が断罪型に寄っている可能性",
               " ".join(accusing) + " ← 矛先を返すのではなく、武器か赦しか問いを手渡す")
    else:
        record("PASS", "ビート39 着地", "断罪の定型句なし。型は目視で確認すること")



def check_signature(paras, spec):
    sig = spec["signature"]
    if paras and sig in paras[-1]:
        record("PASS", "シグネチャ", sig)
    else:
        record("FAIL", "シグネチャが末尾にない", f"最終段落を「{sig}」で始まる締めにする")


def check_numbers(mapped, spec):
    d = dict(mapped)
    b3 = d.get(3, "")
    nums = re.findall(r"[0-9０-９]+(?:[.,][0-9０-９]+)?", b3)
    if len(nums) >= 2:
        record("PASS", f"ビート3の数字 {len(nums)}個", "現象の広がりを示す丸めない数字を2つ以上")
    else:
        record("WARN", f"ビート3の数字 {len(nums)}個",
               "現象の広がりのビートには丸めない数字を2つ以上。金額でなくN数・率・件数・種数でよい")

    b1 = d.get(1, "")
    if re.search(r"[0-9０-９]", b1):
        record("WARN", "ビート1に数字がある",
               "開幕の一撃は情景か逆説の一行にする。統計・金額から始めない")


def print_verbose(mapped, spec):
    by_n = {b["n"]: b for b in spec["beats"]}
    print("\nビート別字数")
    print("-" * 58)
    cur_block = None
    for n, text in mapped:
        b = by_n.get(n)
        if not b:
            print(f"  +{n:>2}  (設計図外の余剰段落)          {body_len(text):>5}字")
            continue
        if b["block"] != cur_block:
            cur_block = b["block"]
            print(f"[ブロック{cur_block}] {spec['blocks'][cur_block]['name']}")
        a, t = body_len(text), b["target"]
        mark = "OK " if a >= t * spec["beat_ratio_min"] else "薄い"
        print(f"  {n:>2}  {b['name']:<12} {a:>5}字 / 目標{t:>4}字  {mark}")
    print("-" * 58)


def main():
    ap = argparse.ArgumentParser(description="台本の機械監査")
    ap.add_argument("path", help="台本本文のプレーンテキスト")
    ap.add_argument("--verbose", "-v", action="store_true", help="ビート別字数の一覧を出す")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"ファイルが見つからない: {args.path}", file=sys.stderr)
        return 2

    spec = json.load(open(SPEC_PATH, encoding="utf-8"))
    paras = load_paragraphs(args.path)
    if not paras:
        print("本文が空", file=sys.stderr)
        return 2

    mapped, exact = map_beats(paras, spec)

    total = check_length(paras, spec)
    check_paragraphs(paras, spec, exact)
    check_beat_lengths(mapped, spec)
    check_heavy_beats(mapped, spec)
    check_question_ends(mapped, spec)
    check_twist_position(mapped, spec, total)
    check_numbers(mapped, spec)
    check_tts(paras, spec)
    check_style(mapped, spec)
    check_engagement(mapped, spec)
    check_meta(mapped, spec)
    check_ending(mapped, spec)
    check_signature(paras, spec)

    print(f"監査対象: {args.path}")
    print("=" * 58)
    for level, label, detail in RESULTS:
        mark = {"PASS": "[  OK  ]", "WARN": "[ WARN ]", "FAIL": "[ FAIL ]"}[level]
        print(f"{mark} {label}")
        if detail:
            print(f"         {detail}")
    print("=" * 58)

    if args.verbose:
        print_verbose(mapped, spec)

    fails = sum(1 for r in RESULTS if r[0] == "FAIL")
    warns = sum(1 for r in RESULTS if r[0] == "WARN")
    est_min = total / 320  # AI音声の実測レート(約320字/分)
    print(f"\n総字数 {total:,}字 / 段落 {len(paras)} / 推定尺 約{est_min:.1f}分")
    if fails:
        print(f"判定: 不合格(FAIL {fails}件、WARN {warns}件)")
        print("削るのではなく増築して再監査すること。優先順位は references/audit.md を参照")
        return 1
    print(f"判定: 合格(WARN {warns}件)")
    print("次は references/audit.md の目視チェックへ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
