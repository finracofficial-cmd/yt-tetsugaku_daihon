import json, subprocess, sys, urllib.parse, os

os.environ['SSL_CERT_FILE']='/root/.ccr/ca-bundle.crt'
os.environ['REQUESTS_CA_BUNDLE']='/root/.ccr/ca-bundle.crt'

QUERIES = [
 "なぜ 心理学 解説", "なぜ 人は のか 解説", "進化心理学 解説", "行動経済学 解説",
 "恋愛 心理学 なぜ", "社会 構造 解説 なぜ", "研究 でわかった 解説", "論文 解説 心理",
 "雑学 なぜ 解説", "ゆっくり解説 心理学", "人間関係 心理 解説", "脳科学 解説 なぜ",
 "残酷な真実 解説", "日本 現実 解説 なぜ", "格差 解説 なぜ", "モテる 科学 解説",
]
SP_WEEK = "EgQIAxAB"

def search(q):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&sp={SP_WEEK}"
    try:
        out = subprocess.run(["yt-dlp","--flat-playlist","-J","--playlist-end","150",url],
                             capture_output=True, timeout=240)
        d = json.loads(out.stdout)
        return d.get("entries") or []
    except Exception as e:
        print(f"  !! {q}: {e}", file=sys.stderr); return []

seen = {}
for q in QUERIES:
    ents = search(q)
    print(f"{q}: {len(ents)}", file=sys.stderr)
    for e in ents:
        if not e.get("id"): continue
        seen.setdefault(e["id"], e)

print(f"unique={len(seen)}", file=sys.stderr)
json.dump(list(seen.values()), open("raw_flat.json","w"), ensure_ascii=False)
