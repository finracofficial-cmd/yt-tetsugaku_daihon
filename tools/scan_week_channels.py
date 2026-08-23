import json, subprocess, os, sys, re
from concurrent.futures import ThreadPoolExecutor

os.environ['SSL_CERT_FILE']='/root/.ccr/ca-bundle.crt'
os.environ['REQUESTS_CA_BUNDLE']='/root/.ccr/ca-bundle.crt'

pool = {}
for f in ('raw_flat.json','raw_flat2.json'):
    for e in json.load(open(f)):
        if e.get('id'): pool.setdefault(e['id'], e)

# 参照Chと同じ型:「なぜ〜のか」か、学問タグ付き。長尺のみ
GENRE = re.compile(r'なぜ.{2,40}(のか|の。?か)|【[^】]*(心理学|進化|行動経済|社会学|脳科学|経済学|人類学|統計|生物学|遺伝|人口学|哲学|科学)')
NOISE = re.compile(r'海外の反応|大谷|ドジャース|秋篠宮|皇室|短劇|SUB\]|切り抜き|MMA|野球|VIVANT|速報|ゆっくり実況')

chans = {}
for e in pool.values():
    t = e.get('title') or ''
    if (e.get('duration') or 0) < 420: continue
    if NOISE.search(t) or not GENRE.search(t): continue
    cu = e.get('channel_url')
    if cu: chans.setdefault(cu, e.get('channel'))
print(f"ジャンル該当チャンネル {len(chans)}件", file=sys.stderr)

def fetch(cu):
    try:
        out = subprocess.run(["yt-dlp","-J","--flat-playlist","--playlist-end","25",
                              "--no-warnings", cu.rstrip('/')+"/videos"],
                             capture_output=True, timeout=180)
        d = json.loads(out.stdout)
        return {"channel": d.get("channel"), "channel_url": cu,
                "subs": d.get("channel_follower_count"),
                "videos": [{"id":v.get("id"),"title":v.get("title"),
                            "view_count":v.get("view_count"),"duration":v.get("duration")}
                           for v in (d.get("entries") or [])]}
    except Exception:
        return None

res = []
with ThreadPoolExecutor(max_workers=5) as ex:
    for i, r in enumerate(ex.map(fetch, list(chans))):
        if r and r.get("subs") is not None: res.append(r)
        if (i+1) % 10 == 0: print(f"  {i+1}/{len(chans)} (成功{len(res)})", file=sys.stderr)

json.dump(res, open('channels.json','w'), ensure_ascii=False)
print(f"取得 {len(res)}/{len(chans)}", file=sys.stderr)
