"""Bildbeschaffung: Unsplash (Unsplash License, kommerziell frei) und NASA (gemeinfrei)."""
import json, os, sys, hashlib, urllib.parse, urllib.request

UA = {"User-Agent": "rubic-shorts/1.0"}
CACHE = os.path.expanduser("~/rubic-cache/photos")


def _get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def unsplash_key():
    k = os.environ.get("UNSPLASH_KEY")
    if not k:
        p = os.path.expanduser("~/nikki/.unsplash_key")
        if os.path.exists(p):
            k = open(p).read().strip()
    if not k:
        sys.exit("UNSPLASH_KEY fehlt")
    return k


def unsplash(query, used, orientation="portrait"):
    """Liefert (pfad, meta). Überspringt bereits verwendete Foto-IDs."""
    os.makedirs(CACHE, exist_ok=True)
    key = unsplash_key()
    h = {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}
    q = urllib.parse.urlencode({"query": query, "orientation": orientation,
                                "per_page": 30, "content_filter": "high"})
    data = json.loads(_get(f"https://api.unsplash.com/search/photos?{q}", h))
    res = data.get("results", [])
    if not res and orientation:
        return unsplash(query, used, orientation=None)
    for p in res:
        if p["id"] in used:
            continue
        if min(p["width"], p["height"]) < 1600:
            continue
        # keine Fotos mit erkennbaren Personen im Vordergrund bevorzugen
        tags = " ".join(t.get("title", "") for t in p.get("tags", []))
        if any(w in tags for w in ("man", "woman", "person", "people", "girl", "boy")):
            continue
        path = os.path.join(CACHE, f"u_{p['id']}.jpg")
        if not os.path.exists(path):
            raw = p["urls"]["raw"] + "&w=2200&q=88&fm=jpg"
            open(path, "wb").write(_get(raw, timeout=120))
            # Download-Tracking laut Unsplash-API-Richtlinien
            try:
                _get(p["links"]["download_location"], h)
            except Exception:
                pass
        return path, {"source": "unsplash", "id": p["id"],
                      "author": p["user"]["name"], "url": p["links"]["html"]}
    raise RuntimeError(f"Kein passendes Unsplash-Foto für '{query}'")


def nasa(query, used):
    os.makedirs(CACHE, exist_ok=True)
    q = urllib.parse.urlencode({"q": query, "media_type": "image"})
    data = json.loads(_get(f"https://images-api.nasa.gov/search?{q}"))
    for item in data["collection"]["items"]:
        nid = item["data"][0]["nasa_id"]
        if nid in used:
            continue
        try:
            assets = json.loads(_get(item["href"]))
        except Exception:
            continue
        cands = [a for a in assets if a.lower().endswith((".jpg", ".jpeg"))]
        orig = [a for a in cands if "~orig" in a] or [a for a in cands if "~large" in a]
        if not orig:
            continue
        url = orig[0].replace("http://", "https://").replace(" ", "%20")
        path = os.path.join(CACHE, "n_" + hashlib.md5(nid.encode()).hexdigest() + ".jpg")
        if not os.path.exists(path):
            open(path, "wb").write(_get(url, timeout=180))
        return path, {"source": "nasa", "id": nid, "title": item["data"][0].get("title", "")}
    raise RuntimeError(f"Kein NASA-Bild für '{query}'")


def fetch(spec, used):
    """spec: {"unsplash": "query"} | {"nasa": "query"} | {"id": "u_xxx"}"""
    if "nasa" in spec:
        return nasa(spec["nasa"], used)
    return unsplash(spec["unsplash"], used)
