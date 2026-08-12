#!/usr/bin/env python3
"""audit.py の自己テスト(v4.0)。

仕様を満たす合成台本を組み立てて合格することと、
v4.0で新たに導入した判定が欠陥を正しく捕まえることを確認する。

    python3 tools/test_audit.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "tools", "audit.py")
SPEC = json.load(open(os.path.join(ROOT, "tools", "beats.json"), encoding="utf-8"))

# 研究語も数字も含まない繋ぎ文。1文32字。
FILLER = "その仕組みは、気づかれないまま人の判断を静かに書き換えていく。"

SCENE_OPEN = "夜のコンビニ。あなたは、レジの前で財布の中の小銭を指先で探している。"
CALLBACK = "もう一度、あの夜のコンビニに戻る。財布の小銭を指先で探すあなたは、もう同じ人ではない。"


def pad(head, target):
    """head の後ろに繋ぎ文を足して、目標字数に近づける。"""
    body = head
    while len(body) + len(FILLER) <= target:
        body += FILLER
    return body


def build(**defect):
    """v4.0の仕様を満たす40段落の合成台本を作る。defect で欠陥を注入する。"""
    p = {}

    # 開幕 P1〜P5(820字)
    p[1] = pad(SCENE_OPEN, 160)
    p[2] = pad("あなたにも心当たりがあるのではないだろうか。同じ場面を、想像してみてほしい。", 160)
    p[3] = pad("2015年、東京大学の研究チームが被験者42人に同じ課題を出した。正答率は85パーセント対20パーセントで分かれた。", 170)
    p[4] = pad("多くの人はここで、意志の弱さのせいだと考える。", 160)
    p[5] = pad("今日はそれを、心理学と経済学から解剖してみたい。", 160)

    # 展開 P6〜P33(4,540字)。研究は前半と後半に置き、P12〜P19を研究ゼロの区間にする。
    p[6] = pad("1998年、コロンビア大学の実験では、参加者390人の選択が二つに割れた。", 210)
    p[7] = pad("追加の調査では、同じ傾向が別の集団でも観察されている。", 210)
    p[8] = pad("これはSNSで言えば、既読をつけたまま返信を遅らせる行為に近い。", 170)
    p[9] = pad("それは単なる思い込みではないか、と思うかもしれない。だが、話はもっと大きかった。", 170)
    p[10] = pad("2003年、心理学者のチームが被験者128人を二群に分けて追跡した。差は13.68倍に開いた。", 230)
    p[11] = pad("同じ論文には、もうひとつの数字がある。効果は3年後にも残っていた。", 210)
    # ここから研究ゼロの区間(数字も研究語も出さない)
    p[12] = pad("ここで、数字をいったん置く。", 160)
    p[13] = pad("朝の駅のホーム。あなたの前に立つ男が、スマホの画面を何度も上下に滑らせている。", 160)
    p[14] = pad("それは、財布の底に沈んだレシートを数えなおすようなものだ。", 160)
    p[15] = pad("その動作に、名前はついているのだろうか。", 160)
    p[16] = pad("同じことが、あなたの一日にも起きている。あなたが気づいていないだけだ。", 160)
    p[17] = pad("それでも人は、自分だけは違うと考える。", 160)
    p[18] = pad("そんなものは気の持ちようではないか、と思うかもしれない。ところが、そう単純でもない。", 170)
    p[19] = pad("たとえるなら、傾いた床の上で、まっすぐ立っているつもりでいる状態に近い。", 160)
    # 研究ゼロの区間はここまで
    p[20] = pad("2011年、行動経済学者が1万2400人の家計簿を解析した。差は0.87パーセントだった。", 210)
    p[21] = pad("この調査には続きがある。追跡は7年に及んだ。", 210)
    p[22] = pad("では、あなたはそこで何を手放しているのだろうか。", 160)
    p[23] = pad("夕方の台所。あなたは冷蔵庫の窓に映る自分の顔を、一瞬だけ見る。", 160)
    p[24] = pad("これは、暗号を送る側と受け取る側が、別の鍵を持っているのと同じ構造にある。", 160)
    p[25] = pad("2007年、霊長類学者が147種の観察記録を並べ直した。頻度は種ごとに5倍以上ちがった。", 210)
    p[26] = pad("同じデータには、群れの大きさとの相関も出ている。", 210)
    p[27] = pad("ただしこの効果には限界がある。396人での追試では再現されなかった。", 180)
    p[28] = pad("それなら結論は出ているのではないか、と思うかもしれない。しかし、議論はまだ続いている。", 180)
    p[29] = pad("パソコンに例えれば、計算する部分ではなく、配線だけが速い状態にあたる。", 160)
    p[30] = pad("2019年、国立の研究所が2万8000件の記録を突き合わせた。差は115回分に相当した。", 210)
    p[31] = pad("この数字は、別の調査でもほぼ同じ幅で再現されている。", 210)
    p[32] = pad("これは、農耕が始まってからの数千年ではなく、進化の側に理由がある。", 180)
    p[33] = pad("では、その仕組みは誰のために働いているのだろうか。", 160)

    # 着地 P34〜P40(940字)
    p[34] = pad(CALLBACK, 150)
    p[35] = pad("あの小銭を探す指先が何を測っていたのか、もう見当がついている。", 150)
    p[36] = pad("あなたの前に出てきたものが、ようやく一続きの線になる。", 140)
    p[37] = pad("それでも自分には関係ない、と思うかもしれない。ところが、この線はもっと手前から始まっている。", 150)
    p[38] = pad("あなたから奪われているのは金ではなく、選び直すまでの時間である。", 130)
    p[39] = pad("それは怠惰ではない。名前のある仕組みだった。名前がつけば、手放すこともできる。", 130)
    p[40] = (SPEC["signature"] +
             "よろしければチャンネル登録と高評価をお願いします。それでは次の動画で、またお会いしましょう。")

    if defect.get("no_free_decile"):
        for i in range(1, 40):
            p[i] = p[i] + "2020年の調査では、対象は3400人だった。"
    if defect.get("long_study_run"):
        p[20] = ("2011年、行動経済学者が1万2400人の家計簿を解析した。"
                 "対象は35歳から54歳の1200世帯である。脱落したのは120人だった。"
                 "差は0.87パーセントだった。回答率は92パーセントだった。") + FILLER * 2
    if defect.get("no_callback"):
        p[34] = pad("ここまでの道のりを、いちど整理しておこう。", 150)
        p[35] = pad("出てきたものを、順に並べ直す。", 150)
    if defect.get("open_number"):
        p[1] = pad("3人に1人が、同じ場面で立ち止まる。", 160)
    if defect.get("no_signature"):
        p[40] = "おわり。またお会いしましょう。"
    if defect.get("forbidden_char"):
        p[8] = p[8].replace("。", "【重要】。", 1)

    return "\n\n".join(p[i] for i in range(1, 41))


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        r = subprocess.run([sys.executable, AUDIT, path], capture_output=True, text=True)
        return r.returncode, r.stdout
    finally:
        os.unlink(path)


def fails(out):
    return [l for l in out.splitlines() if l.startswith("[ FAIL ]")]


def main():
    bad = []

    code, out = run(build())
    if code != 0:
        bad.append("仕様準拠の台本が不合格になった:\n" + "\n".join(fails(out)))

    cases = [
        ("no_free_decile", "研究ゼロの区間", "研究の出てこない区間"),
        ("long_study_run", "研究文の長すぎる連続", "研究文の最長連続"),
        ("no_callback", "冒頭への回帰の欠落", "冒頭への回帰がない"),
        ("open_number", "冒頭の数字", "冒頭に数字がある"),
        ("no_signature", "シグネチャの欠落", "シグネチャが末尾にない"),
        ("forbidden_char", "禁止記号", "禁止記号を検出"),
    ]
    for key, name, marker in cases:
        code, out = run(build(**{key: True}))
        if code == 0:
            bad.append(f"{name}を入れた台本が合格してしまった")
        elif not any(marker in l for l in fails(out)):
            bad.append(f"{name}が、期待した項目({marker})では捕まっていない")

    if bad:
        for b in bad:
            print("NG: " + b)
        return 1
    print(f"OK: audit.py は仕様準拠を合格、欠陥{len(cases)}種を正しく不合格と判定した")
    return 0


if __name__ == "__main__":
    sys.exit(main())
