import json, subprocess, sys, urllib.parse, os
from concurrent.futures import ThreadPoolExecutor

os.environ['SSL_CERT_FILE']='/root/.ccr/ca-bundle.crt'
os.environ['REQUESTS_CA_BUNDLE']='/root/.ccr/ca-bundle.crt'

# 参照Chと同じ「型」を狙う。なぜ〜のか型 × 学問タグ × 長尺解説
QUERIES = [
 "なぜ のか 心理学", "なぜ のか 進化心理学", "なぜ のか 行動経済学", "なぜ のか 社会学",
 "なぜ 人間は のか 解説", "なぜ 人は のか 進化", "心理学 解剖 なぜ", "教養 解説 なぜ のか",
 "恋愛 進化心理学 解説", "モテ 心理学 なぜ", "人間関係 進化心理学", "残酷 心理学 解説 なぜ",
 "なぜ のか 脳科学", "なぜ のか 経済学 解説", "なぜ のか 生物学 解説", "なぜ のか 統計",
 "科学的に なぜ 解説", "研究でわかった なぜ のか", "本能 なぜ 解説 心理",
 "なぜ 現代人は のか", "なぜ 日本人は のか 解説", "なぜ 女性は のか 心理",
 "なぜ 男性は のか 心理", "なぜ 若者は のか 解説", "自己家畜化 解説", "シグナル理論 解説",
]
SP_WEEK = "EgQIAxAB"

def search(q):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&sp={SP_WEEK}"
    try:
        out = subprocess.run(["yt-dlp","--flat-playlist","-J","--playlist-end","120",url],
                             capture_output=True, timeout=240)
        return json.loads(out.stdout).get("entries") or []
    except Exception as e:
        print(f"  !! {q}: {e}", file=sys.stderr); return []

seen = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for q, ents in zip(QUERIES, ex.map(search, QUERIES)):
        print(f"{q}: {len(ents)}", file=sys.stderr)
        for e in ents:
            if e.get("id"): seen.setdefault(e["id"], e)

print(f"unique={len(seen)}", file=sys.stderr)
json.dump(list(seen.values()), open("raw_flat2.json","w"), ensure_ascii=False)
