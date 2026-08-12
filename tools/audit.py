#!/usr/bin/env python3
"""台本の機械監査 v5.0(工程4・第1段階)

使い方:
    python3 tools/audit.py output/<dir>/03_台本.txt
    python3 tools/audit.py output/<dir>/03_台本.txt --verbose

入力は本文のみのプレーンテキスト。段落は空行で区切る。
FAILが1つでもあれば終了コード1を返す。

判定は2群に分かれる。

  模倣  参照チャンネル全92本の分布(p10〜p90)に合わせる帯
  自前  参照とは意図的にずらしている本チャンネルの規律

しきい値は「再生数を上げる条件」ではない。全92本で18指標と再生数の
順位相関を取ったが、多重比較の補正後に有意なものは一つも無かった。
根拠は knowledge/reference-channel/script-analysis.md の v5.0 較正節。
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
    return [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=。)", text) if s.strip()]


def strip_quotes(text):
    """かぎ括弧内の引用を除去(敬語・煽り語の誤検出を避けるため)。"""
    return re.sub(r"「[^」]*」", "", text)


def scale(paras, rng, pad=1):
    """40段落基準で書かれた段落範囲を、実際の段落数に比例させる。1始まりの閉区間。"""
    n = len(paras)
    a, b = rng
    lo = max(1, round(a * n / 40) - pad)
    hi = min(n, round(b * n / 40) + pad)
    return lo, hi


def in_range(i, rng, paras):
    lo, hi = scale(paras, rng)
    return lo <= i <= hi


# --------------------------------------------------------------------------
# 全体量
# --------------------------------------------------------------------------

def check_length(paras, spec):
    total = sum(body_len(p) for p in paras)
    if total < spec["body_min"] or total > spec["body_max"]:
        record("FAIL", f"本文の総字数 {total:,}字",
               f"許容{spec['body_min']:,}〜{spec['body_max']:,}字。参照92本の実測は3,043〜9,735字")
    elif total < spec["body_soft_min"] or total > spec["body_max_soft"]:
        record("WARN", f"本文の総字数 {total:,}字",
               f"目安{spec['body_soft_min']:,}〜{spec['body_max_soft']:,}字(参照92本の中央値6,446字)")
    else:
        record("PASS", f"本文の総字数 {total:,}字", f"目安{spec['body_target']:,}字")
    return total


def check_sentences(paras, spec):
    sents = [s for p in paras for s in split_sentences(p)]
    n = len(sents)
    lo, hi = spec["sentence_soft_min"], spec["sentence_soft_max"]
    if n < spec["sentence_min"] or n > spec["sentence_max_total"]:
        record("FAIL", f"総文数 {n}文",
               f"許容{spec['sentence_min']}〜{spec['sentence_max_total']}文。参照92本は93〜288文")
    elif lo <= n <= hi:
        record("PASS", f"総文数 {n}文", f"目安{lo}〜{hi}文(参照92本の中央値186文)")
    else:
        record("WARN", f"総文数 {n}文", f"目安{lo}〜{hi}文(参照92本の中央値186文)")

    med = sorted(body_len(s) for s in sents)[n // 2] if n else 0
    mlo, mhi = spec["sentence_len_med_min"], spec["sentence_len_med_max"]
    if mlo <= med <= mhi:
        record("PASS", f"一文の長さの中央値 {med}字", f"目安{mlo}〜{mhi}字(参照92本の中央値31字)")
    else:
        record("WARN", f"一文の長さの中央値 {med}字", f"目安{mlo}〜{mhi}字(参照92本の中央値31字)")
    return n


def check_paragraphs(paras, spec):
    n = len(paras)
    t, lo, hi = spec["paragraph_target"], spec["paragraph_min"], spec["paragraph_max"]
    if n == t:
        record("PASS", f"段落数 {n}", f"目標{t}")
    elif lo <= n <= hi:
        record("PASS", f"段落数 {n}", f"許容{lo}〜{hi}(目標{t})")
    else:
        record("FAIL", f"段落数 {n}", f"許容{lo}〜{hi}から外れている")


def check_para_weight(paras, spec):
    lo, hi = spec["para_len_min"], spec["para_len_max"]
    lens = [body_len(p) for p in paras]
    thin = [(i + 1, L) for i, L in enumerate(lens) if L < lo]
    fat = [(i + 1, L) for i, L in enumerate(lens) if L > hi]
    # 段落の長さは参照から導出できない(文字起こしに段落の区切りが無い)。WARNに留める。
    if thin:
        record("WARN", f"短い段落 {len(thin)}件",
               " ".join(f"P{i}({L}字)" for i, L in thin[:8]) +
               f" ← 目安下限{lo}字。一撃の一行なら問題ない")
    if fat:
        record("WARN", f"長すぎる段落 {len(fat)}件",
               " ".join(f"P{i}({L}字)" for i, L in fat[:8]) + f" ← 目安上限{hi}字。分割を検討")
    if not thin and not fat:
        record("PASS", "段落の長さ", f"全段落が{lo}〜{hi}字に収まる")

    hv = spec["heavy_para_chars"]
    n_hv = sum(1 for L in lens if L >= hv)
    if n_hv >= spec["heavy_para_min"]:
        record("PASS", f"重量段落({hv}字以上) {n_hv}件", f"下限{spec['heavy_para_min']}件")
    else:
        record("FAIL", f"重量段落({hv}字以上) {n_hv}件",
               f"下限{spec['heavy_para_min']}件。主役研究を手順から描いた段落が足りない")


def check_layers(paras, spec):
    total = sum(body_len(p) for p in paras)
    got = {}
    for i, p in enumerate(paras, 1):
        L = body_len(p)
        for layer in spec["layers"]:
            lo, hi = scale(paras, layer["paras"], pad=0)
            if lo <= i <= hi:
                got[layer["key"]] = got.get(layer["key"], 0) + L
                break
    bad = []
    for layer in spec["layers"]:
        a = got.get(layer["key"], 0)
        t = layer["target"]
        if a < t * 0.7 or a > t * 1.4:
            bad.append(f"{layer['name']} {a:,}字(目安{t:,}字)")
    if bad:
        record("WARN", "層ごとの字数配分が目安から外れている", " / ".join(bad))
    else:
        record("PASS", "層ごとの字数配分",
               " / ".join(f"{l['name']}{got.get(l['key'],0):,}字" for l in spec["layers"]))


# --------------------------------------------------------------------------
# 錨
# --------------------------------------------------------------------------

def check_open(paras, spec):
    """冒頭の一撃。

    v4.0までは「P1に数字があればFAIL」としていたが、これは手作業の4本だけを見た
    判断だった。参照92本では第1文の41パーセントが数字を含み、10パーセントは数字で
    始まっている(「2022年度、日本の企業が交際費として計上した金額は」のような
    統計始まりの回も実在する)。したがって数字の有無では落とさない。
    数字で始まる書き出しだけを、少数派としてWARNで知らせる。
    """
    p1 = paras[0]
    if re.match(r"^[0-9０-９]", p1.lstrip()):
        record("WARN", "冒頭が数字で始まっている",
               "参照92本でも10パーセントは数字始まりなので誤りではない。"
               "ただし多数派は情景か逆説の一行である")
    else:
        record("PASS", "冒頭の一撃", "情景か逆説で始まっている")


def check_first_data(paras, spec, total):
    study = re.compile(spec["patterns"]["study"])
    cum = 0
    hit_i, hit_ratio = None, None
    for i, p in enumerate(paras, 1):
        for s in split_sentences(p):
            cum += body_len(s)
            if hit_i is None and study.search(s):
                hit_i, hit_ratio = i, cum / total
    if hit_i is None:
        record("FAIL", "実データが一度も出てこない", "研究・統計を入れる")
        return
    late = spec["imitation"]["first_data_late_ratio"]
    label = f"最初の実データ P{hit_i}({hit_ratio*100:.0f}パーセント地点)"
    if hit_ratio > late:
        record("WARN", label,
               f"遅い。参照92本の中央値は3パーセント地点、最も遅い回でも20パーセント地点")
    else:
        record("PASS", label, "参照92本の中央値は3パーセント地点。早く出してよい")


def _tokens(text):
    return set(re.findall(r"[一-龥]{2,4}|[ァ-ヴー]{3,}", text))


def _motif(paras):
    """冒頭2段落から、回帰の目印になる語を拾う。

    台本全体に散らばっている語は冒頭固有の目印にならないので、
    段落の3分の1超に出る語は落とす。
    """
    head = paras[0] + (paras[1] if len(paras) > 1 else "")
    stop = {"自分", "人間", "私たち", "我々", "とき", "こと", "もの", "場合", "本当",
            "相手", "今日", "世界", "問題", "理由", "意味", "状態", "以上", "以下"}
    df = {}
    for p in paras:
        for w in _tokens(p):
            df[w] = df.get(w, 0) + 1
    limit = len(paras) / 3
    return {w for w in _tokens(head) if w not in stop and df.get(w, 0) <= limit}


def check_callback(paras, spec):
    rng = next(a["paras"] for a in spec["anchors"] if a["id"] == "callback")
    lo, hi = scale(paras, rng)
    motif = _motif(paras)
    best, best_i = 0, None
    for i in range(lo, min(hi, len(paras)) + 1):
        k = len(_tokens(paras[i - 1]) & motif)
        if k > best:
            best, best_i = k, i
    if best >= 2:
        record("PASS", f"冒頭の情景への回帰 P{best_i}",
               f"共通語{best}語。参照92本のうち47本(51パーセント)が実行、位置の中央値は90パーセント地点")
    else:
        record("WARN", f"着地帯(P{lo}〜P{hi})に冒頭への回帰が見つからない",
               "参照でも実行は51パーセントで必須ではない。入れるなら「振り返ろう」と言わず、"
               "冒頭の情景そのものに戻ってから発見を並べ直す")


def check_signature(paras, spec):
    sig = spec["signature"]
    if paras and sig in paras[-1]:
        record("PASS", "シグネチャ", sig)
    else:
        record("FAIL", "シグネチャが末尾にない", f"最終段落を「{sig}」で締める")


def check_ending(paras, spec):
    text = paras[-2] if len(paras) >= 2 else ""
    accusing = [w for w in spec["accusing_markers"] if w in text]
    if accusing:
        record("WARN", "着地が断罪型に寄っている可能性",
               " ".join(accusing) + " ← 矛先を返さず、武器か赦しか問いを手渡す")
    else:
        record("PASS", "着地", "断罪の定型句なし。4型のどれで着地したかは目視で確認")


# --------------------------------------------------------------------------
# 分布
# --------------------------------------------------------------------------

def check_study_distribution(paras, spec):
    """研究の連続と散らばり。v5.0で大きく緩めた項目である。

    v4.0では参照4本の実測(最長2文)から「3文以上続けない」を規律にしていたが、
    全92本では中央値3文・p90が5文・最大8文だった。4本が偶然短かっただけである。
    「研究ゼロの区間を必ず作る」も同様で、92本中22本は0区間だった。
    """
    im = spec["imitation"]
    study = re.compile(spec["patterns"]["study"])
    sents = [s for p in paras for s in split_sentences(p)]
    n = len(sents)

    run = best = 0
    for s in sents:
        run = run + 1 if study.search(s) else 0
        best = max(best, run)
    soft, hard = im["study_run_soft_max"], im["study_run_hard_max"]
    if best <= soft:
        record("PASS", f"研究文の最長連続 {best}文",
               f"目安{soft}文以内(参照92本は中央値3文、p90が5文)")
    elif best <= hard:
        record("WARN", f"研究文の最長連続 {best}文",
               f"目安{soft}文(参照のp90)を超える。間に意味づけの地の文を挟んで割る")
    else:
        record("FAIL", f"研究文の最長連続 {best}文",
               f"上限{hard}文(参照92本の最大値)を超えている。データの塊が大きすぎる")

    occupied = {min(9, int(i / n * 10)) for i, s in enumerate(sents) if study.search(s)}
    free = 10 - len(occupied)
    lo = im["study_deciles_min"]
    if len(occupied) >= lo:
        record("PASS", f"研究のある区間 {len(occupied)}/10",
               f"下限{lo}区間(参照92本は中央値9区間)。研究ゼロの区間は{free}個"
               f"(参照は中央値1個、92本中22本は0個)")
    else:
        record("WARN", f"研究のある区間 {len(occupied)}/10",
               f"下限{lo}区間。参照92本の中央値は9区間で、データはむしろ全体に散っている")


def check_scene(paras, spec):
    im = spec["imitation"]
    scene = re.compile(spec["patterns"]["scene"])
    hits = [i for i, p in enumerate(paras, 1) if scene.search(p)]
    op = [i for i in hits if in_range(i, im["scene_open_paras"], paras)]
    mid = [i for i in hits if in_range(i, im["scene_mid_paras"], paras)]
    cl = [i for i in hits if in_range(i, im["scene_close_paras"], paras)]
    bad = []
    if not op:
        bad.append("開幕に情景が無い")
    if len(mid) < im["scene_mid_min"]:
        bad.append(f"中盤の情景が{len(mid)}件(下限{im['scene_mid_min']}件)")
    if not cl:
        bad.append("終盤に情景が無い")
    if bad:
        record("WARN", "情景の三点配置が崩れている",
               " / ".join(bad) + " ← 参照92本の中盤の情景は中央値3件")
    else:
        record("PASS", f"情景の三点配置 開幕{len(op)}・中盤{len(mid)}・終盤{len(cl)}",
               f"中盤の目安は{im['scene_mid_good']}件(参照92本の中央値)")


def check_rebuttal(paras, spec):
    ed = spec["editorial"]
    hits = []
    for i, p in enumerate(paras, 1):
        opened = any(k in p for k in spec["rebuttal_openers"])
        turned = (any(k in p for k in spec["rebuttal_turns"])
                  or any(k in p for k in spec["rebuttal_concessions"]))
        if opened and turned:
            hits.append(i)
    lo = ed["rebuttal_min"]
    if len(hits) >= lo:
        record("PASS", f"想定反論の往復 {len(hits)}回", "P" + " P".join(str(i) for i in hits))
    else:
        record("WARN", f"想定反論の往復 {len(hits)}回",
               f"自前の下限{lo}回(参照92本の中央値も3回)。視聴者の反論を代弁して越える段落を足す")

    late_lo, _ = scale(paras, [ed["rebuttal_late_from_para"], 40])
    late = [i for i in hits if i >= late_lo]
    if len(late) >= ed["rebuttal_late_min"]:
        record("PASS", f"後半の反論 {len(late)}回", f"P{late_lo}以降")
    else:
        record("WARN", "後半3割に反論が無い", f"P{late_lo}以降に1回(参照92本の中央値も1回)")

    c = sum(1 for p in paras
            if any(k in p for k in spec["rebuttal_openers"])
            and any(k in p for k in spec["rebuttal_concessions"]))
    if c > ed["concession_max"]:
        record("WARN", f"承認句のある段落 {c}件",
               f"自前の目安{ed['concession_max']}件(参照92本のp90は3件)。"
               "毎回«その指摘は正しい»を置くと装置が透ける")


def check_translation(paras, spec):
    """現代語への翻訳。参照の中央値は1箇所で、これは自前の規律である。"""
    ed = spec["editorial"]
    joined = "\n".join(paras)
    n = sum(joined.count(k) for k in spec["analogy_markers"])
    lo, good = ed["analogy_min"], ed["analogy_good"]
    if n >= good:
        record("PASS", f"現代語への翻訳 {n}箇所", f"自前の目安{good}箇所以上")
    elif n >= lo:
        record("PASS", f"現代語への翻訳 {n}箇所", f"自前の下限{lo}箇所は満たす。目安は{good}箇所")
    else:
        record("WARN", f"現代語への翻訳 {n}箇所",
               f"自前の下限{lo}箇所。参照92本の中央値は1箇所で、ここは意図的に参照より多く取る。"
               "研究や概念を出したら、その場で視聴者の日常の具体物に対応させる")


def check_second_person(paras, spec):
    ed = spec["editorial"]
    joined = "\n".join(paras)
    n = len(re.findall(spec["patterns"]["second_person"], joined))
    lo = ed["second_person_min"]
    if n >= lo:
        record("PASS", f"二人称の呼びかけ {n}回", f"自前の下限{lo}回(参照92本の中央値12回)")
    else:
        record("WARN", f"二人称の呼びかけ {n}回",
               f"自前の下限{lo}回(参照92本はp10が4回、中央値12回)。情景と問いかけを二人称で書き直す")
    ny = len(re.findall(spec["patterns"]["second_person_you"], joined))
    if ny < ed["second_person_you_good"]:
        record("WARN", f"「あなた」自体は {ny}回",
               f"目安{ed['second_person_you_good']}回。参照92本も中央値5回で、"
               "「我々」中心の回もあるため文体上の選択でもある")


def check_questions(paras, spec):
    im = spec["imitation"]
    lo, good = im["question_para_min"], im["question_para_good"]
    hits = [i for i, p in enumerate(paras, 1)
            if p.rstrip().rstrip("。」").endswith("か")]
    if len(hits) >= good:
        record("PASS", f"疑問文で終わる段落 {len(hits)}件", "P" + " P".join(str(i) for i in hits))
    elif len(hits) >= lo:
        record("PASS", f"疑問文で終わる段落 {len(hits)}件", f"目安{good}件(参照92本の疑問文は中央値12文)")
    else:
        record("WARN", f"疑問文で終わる段落 {len(hits)}件",
               f"下限{lo}件。参照92本の疑問文は中央値12文で、最も少ない回でも3文あった")


def check_limitation(paras, spec):
    """限界と反証。参照の中央値は0箇所で、これは完全に自前の規律である。"""
    lo = spec["editorial"]["limitation_min"]
    hits = [i for i, p in enumerate(paras, 1)
            if any(k in p for k in spec["limitation_markers"])]
    if len(hits) >= lo:
        record("PASS", f"限界と反証 {len(hits)}件", "P" + " P".join(str(i) for i in hits))
    else:
        record("WARN", "限界と反証がない",
               "参照92本の中央値は0箇所。模倣ではなく、本チャンネルの事実規律から来る自前の技法である")


def check_macro(paras, spec):
    im = spec["imitation"]
    macro = re.compile(spec["patterns"]["macro"])
    hits = [i for i, p in enumerate(paras, 1) if macro.search(p)]
    if len(hits) >= im["macro_good"]:
        record("PASS", f"巨視化 {len(hits)}件", "進化史・歴史・制度への引き上げ")
    elif len(hits) >= im["macro_min"]:
        record("PASS", f"巨視化 {len(hits)}件", f"目安{im['macro_good']}件(参照92本の中央値6件)")
    else:
        record("WARN", "巨視化がない", "進化史・歴史反転・制度の発明のいずれかへ一度引き上げる")


def check_meta(paras, spec):
    """設計図を音読する言い回し。

    v3.2からv4.0では「参照は本編でメタ発話をしない」として2件超をFAILにしていたが、
    これは手作業の書き起こし4本だけを見た判断だった。全92本では中央値1件・p90が3件・
    最大6件あり、しかも18指標のうち再生数との相関が最も強かったのがこの指標で、
    符号は正(rho=+0.273)である。多重比較の補正後に有意ではないため
    「多いほど伸びる」とは言えないが、「少ないほど良い」の根拠も無い。
    したがってv5.0では、定型化を避けるための上限としてWARNだけを残す。
    """
    im = spec["imitation"]
    lo, hi = scale(paras, [5, 6])
    allowed = set(range(lo, hi + 1))
    hits = []
    for i, p in enumerate(paras, 1):
        if i in allowed:
            continue
        for k in spec["meta_markers"]:
            if k in p:
                hits.append(f"P{i}「{k}」")
    soft, hard = im["meta_soft_max"], im["meta_hard_max"]
    if len(hits) <= soft:
        record("PASS", f"メタ発話 {len(hits)}件", f"目安{soft}件以内(参照92本は中央値1件、p90が3件)")
    elif len(hits) <= hard:
        record("WARN", f"メタ発話 {len(hits)}件",
               " ".join(hits[:6]) + f" ← 目安{soft}件(参照のp90)。転換は宣言せず内容で行う")
    else:
        record("FAIL", f"メタ発話が多すぎる {len(hits)}件",
               " ".join(hits[:8]) + f" ← 上限{hard}件(参照92本の最大値)を超えている")


def check_sentence_len(paras, spec):
    lim = spec["sentence_max"]
    worst, where = 0, None
    for i, p in enumerate(paras, 1):
        for s in split_sentences(p):
            L = body_len(s)
            if L > worst:
                worst, where = L, i
    if worst > lim:
        record("WARN", f"最長の一文 {worst}字(P{where})", f"目安{lim}字以内")


# --------------------------------------------------------------------------
# 表記
# --------------------------------------------------------------------------

def check_tts(paras, spec):
    tts = spec["tts"]
    joined = "\n".join(paras)

    hits = sorted({c for c in tts["forbidden_chars"] + tts["forbidden_colons"] if c in joined})
    if hits:
        record("FAIL", "禁止記号を検出", " ".join(hits) + " ← AI音声が誤読または沈黙する")
    else:
        record("PASS", "禁止記号なし", "")

    bad_dots = []
    for m in re.finditer("・", joined):
        i = m.start()
        prev = joined[i - 1] if i > 0 else ""
        nxt = joined[i + 1] if i + 1 < len(joined) else ""
        if not (re.match(KATAKANA, prev or " ") and re.match(KATAKANA, nxt or " ")):
            bad_dots.append(joined[max(0, i - 8):i + 8].replace("\n", ""))
    if bad_dots:
        record("FAIL", f"列挙用の中黒を検出 {len(bad_dots)}件",
               " / ".join(bad_dots[:5]) + " ← 外国人名の区切りのみ許可")
    else:
        record("PASS", "中黒の用法", "外国人名の区切りのみ")

    allowed = set(tts["allowed_abbreviations"])
    latin = {w for w in re.findall(r"[A-Za-zＡ-Ｚａ-ｚ]{1,}", joined)}
    latin = {w for w in latin if w.upper() not in allowed}
    if latin:
        record("FAIL", f"カタカナ化されていない英字 {len(latin)}件",
               " ".join(sorted(latin)[:12]) + " ← ティンダー等のカタカナ表記に直す")
    else:
        record("PASS", "英字のカタカナ化", "定着略称のみ残存")

    if re.search(r"\d+\s*[%％]", joined):
        record("FAIL", "パーセント記号を検出", "「パーセント」と書く")


def check_style(paras, spec):
    allowed = set(spec["polite_allowed_paras"])
    n = len(paras)
    polite = []
    for i, p in enumerate(paras, 1):
        if i > n - 2 or i in allowed:
            continue
        t = strip_quotes(p)
        t = re.sub(r"(覚|冷|励|澄|済|醒|欺|研)ます", "", t)
        if re.search(r"(です|ます|ください|ましょう)[。、]", t):
            polite.append(f"P{i}")
    if polite:
        record("WARN", f"本文に敬語 {len(polite)}件",
               " ".join(polite) + " ← 敬語は最終2段落のみ。引用文中なら問題なし")
    else:
        record("PASS", "敬語の位置", "最終2段落のみ")

    joined = strip_quotes("\n".join(paras))
    hype = [w for w in spec["tts"]["hype_words"] if w in joined]
    if hype:
        record("WARN", "煽り語を検出", " ".join(hype) + " ← 静かに断定する文体に直す")
    else:
        record("PASS", "煽り語なし", "")


# --------------------------------------------------------------------------

def print_verbose(paras, spec):
    study = re.compile(spec["patterns"]["study"])
    scene = re.compile(spec["patterns"]["scene"])
    macro = re.compile(spec["patterns"]["macro"])
    print("\n段落別")
    print("-" * 66)
    cur = None
    for i, p in enumerate(paras, 1):
        layer = None
        for l in spec["layers"]:
            lo, hi = scale(paras, l["paras"], pad=0)
            if lo <= i <= hi:
                layer = l["name"]
        if layer != cur:
            cur = layer
            print(f"[{cur}]")
        tags = []
        if study.search(p):
            tags.append("研究")
        if scene.search(p):
            tags.append("情景")
        if macro.search(p):
            tags.append("巨視")
        if any(k in p for k in spec["rebuttal_openers"]):
            tags.append("反論")
        if any(k in p for k in spec["analogy_markers"]):
            tags.append("翻訳")
        if any(k in p for k in spec["limitation_markers"]):
            tags.append("限界")
        if p.rstrip().rstrip("。」").endswith("か"):
            tags.append("問い")
        L = body_len(p)
        mark = "重" if L >= spec["heavy_para_chars"] else (" " if L >= spec["para_len_min"] else "薄")
        print(f"  P{i:>2} {mark} {L:>4}字  {' '.join(tags)}")
    print("-" * 66)


def main():
    ap = argparse.ArgumentParser(description="台本の機械監査 v4.0")
    ap.add_argument("path", help="台本本文のプレーンテキスト")
    ap.add_argument("--verbose", "-v", action="store_true", help="段落別の一覧を出す")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"ファイルが見つからない: {args.path}", file=sys.stderr)
        return 2

    spec = json.load(open(SPEC_PATH, encoding="utf-8"))
    paras = load_paragraphs(args.path)
    if not paras:
        print("本文が空", file=sys.stderr)
        return 2

    total = check_length(paras, spec)
    check_sentences(paras, spec)
    check_paragraphs(paras, spec)
    check_para_weight(paras, spec)
    check_layers(paras, spec)

    check_open(paras, spec)
    check_first_data(paras, spec, total)
    check_callback(paras, spec)
    check_ending(paras, spec)
    check_signature(paras, spec)

    check_study_distribution(paras, spec)
    check_scene(paras, spec)
    check_rebuttal(paras, spec)
    check_translation(paras, spec)
    check_second_person(paras, spec)
    check_questions(paras, spec)
    check_limitation(paras, spec)
    check_macro(paras, spec)
    check_meta(paras, spec)
    check_sentence_len(paras, spec)

    check_tts(paras, spec)
    check_style(paras, spec)

    print(f"監査対象: {args.path}")
    print("=" * 66)
    for level, label, detail in RESULTS:
        mark = {"PASS": "[  OK  ]", "WARN": "[ WARN ]", "FAIL": "[ FAIL ]"}[level]
        print(f"{mark} {label}")
        if detail:
            print(f"         {detail}")
    print("=" * 66)

    if args.verbose:
        print_verbose(paras, spec)

    fails = sum(1 for r in RESULTS if r[0] == "FAIL")
    warns = sum(1 for r in RESULTS if r[0] == "WARN")
    est_min = total / 320
    print(f"\n総字数 {total:,}字 / 段落 {len(paras)} / 推定尺 約{est_min:.1f}分")
    if fails:
        print(f"判定: 不合格(FAIL {fails}件、WARN {warns}件)")
        print("直し方は references/audit.md を参照")
        return 1
    print(f"判定: 合格(WARN {warns}件)")
    print("次は references/audit.md の目視チェックへ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
