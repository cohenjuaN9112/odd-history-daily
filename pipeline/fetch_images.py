"""Download the Wikimedia Commons images a story needs.

Usage: python3 fetch_images.py stories/<slug>
Reads story.json -> "images": {"key": "Exact Commons file title.jpg", ...}
Writes stories/<slug>/img/<key>.<ext> and img/credits.json (license + author + page URL).
Only public-domain / CC0 / "No restrictions" files are accepted unless "allow_cc_by": true,
in which case the credit line must go in the YouTube description.
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request

UA = "OddHistoryDailyBot/1.0 (personal YouTube project; low volume)"
FREE = ("public domain", "pd", "cc0", "no restrictions")

def get(url, tries=5):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://commons.wikimedia.org/"}), timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < tries - 1 and "robot policy" not in str(e.msg):  # robot-policy refusals do not clear by waiting
                time.sleep(15 * (k + 1)); continue
            raise

def page_info(title):
    """Fallback when the Commons API answers 429 (it rate-limits this client hard): read the same metadata
    from the file description page HTML (license template, author, original URL and size)."""
    t = get("https://commons.wikimedia.org/wiki/" + urllib.parse.quote("File:" + title.replace(" ", "_"))).decode("utf-8", "replace")
    t = t.replace("&#95;", "_")
    txt = lambda x: html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<style.*?</style>", "", x, flags=re.S)))).strip()
    lic = list(dict.fromkeys(txt(x) for x in re.findall(r'class="licensetpl_short"[^>]*>(.*?)</span>', t, re.S)))
    m = re.search(r'id="fileinfotpl_aut"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', t, re.S)
    artist = txt(m.group(1)).replace("Unknown author Unknown author", "Unknown author")[:120] if m else ""
    m = re.search(r'<div class="fullMedia">(?:<p>|<bdi[^>]*>)<a href="(https://upload\.wikimedia\.org/[^"]+)"', t)
    url = html.unescape(m.group(1)).split("?")[0] if m else None
    m = re.search(r'class="fileInfo">\(?\s*([\d,]+)\s*(?:&#215;|\u00d7)\s*([\d,]+)\s*pixels', t)
    w, h = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))) if m else (0, 0)
    if not url: return None
    return {"url": url, "width": w, "height": h, "descriptionurl": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(title.replace(" ", "_")),
            "extmetadata": {"LicenseShortName": {"value": "; ".join(lic) or "?"}, "Artist": {"value": artist}}}

def main(story_dir):
    story = json.load(open(f"{story_dir}/story.json"))
    allow_by = story.get("allow_cc_by", False)
    os.makedirs(f"{story_dir}/img", exist_ok=True)
    old = {}
    if os.path.exists(f"{story_dir}/img/credits.json"):
        old = json.load(open(f"{story_dir}/img/credits.json"))
    credits = {}
    for key, title in story["images"].items():
        if key in old and old[key].get("title") != title:
            for fn in os.listdir(f"{story_dir}/img"):
                if os.path.splitext(fn)[0] == key: os.remove(f"{story_dir}/img/{fn}")
        q = urllib.parse.urlencode({"action": "query", "titles": "File:" + title, "prop": "imageinfo",
                                    "iiprop": "url|size|extmetadata", "format": "json"})
        try:
            d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q, tries=2))
            page = next(iter(d["query"]["pages"].values()))
            ii = page["imageinfo"][0] if "imageinfo" in page else None
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            ii = page_info(title); time.sleep(3)
        if not ii:
            print("MISSING", key, title); continue
        m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "?")
        artist = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()[:120]
        free = any(f in lic.lower() for f in FREE)
        if not free and not (allow_by and lic.lower().startswith("cc by")):
            print("SKIP (license)", key, lic); continue
        # Wikimedia only serves standard thumbnail widths without rate limits (3840/1920/1280/960...)
        w = ii.get("width", 0); url = ii["url"]
        std = next((s for s in (3840, 1920, 1280, 960) if w >= s), None)
        if std and not url.lower().endswith((".svg", ".gif")):
            path = urllib.parse.urlparse(url).path            # /wikipedia/commons/a/ab/Name.jpg
            parts = path.split("/"); name = parts[-1]
            url = "https://upload.wikimedia.org" + "/".join(parts[:3]) + "/thumb/" + "/".join(parts[3:]) + f"/{std}px-{name}"
            if name.lower().endswith((".tif", ".tiff")): url += ".jpg"
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
        out = f"{story_dir}/img/{key}{ext}"
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            try:
                data = get(url, tries=5 if std else 2)
            except urllib.error.HTTPError as e:
                if e.code != 429 or w < 500: raise
                if std:  # an uncached thumbnail size can be refused ("robot policy"); try the smaller standard sizes once
                    data = None
                    for s2 in (1920, 1280, 960, 500):
                        if s2 >= std: continue
                        try: data = get(url.replace(f"/{std}px-", f"/{s2}px-"), tries=1); print("  smaller thumbnail", s2, key); break
                        except urllib.error.HTTPError: time.sleep(5)
                    if data is None: raise
                    open(out, "wb").write(data); time.sleep(3)
                    credits[key] = {"file": os.path.basename(out), "title": title, "license": lic, "author": artist,
                                    "page": ii.get("descriptionurl"), "size": [ii.get("width"), ii.get("height")]}
                    print("OK", key, lic, ii.get("width"), ii.get("height")); continue
                # originals of small files get rate limited; fall back to the 500px standard thumbnail
                parts = urllib.parse.urlparse(url).path.split("/"); name = parts[-1]
                data = get("https://upload.wikimedia.org" + "/".join(parts[:3]) + "/thumb/" + "/".join(parts[3:]) + f"/500px-{name}")
            open(out, "wb").write(data); time.sleep(3)
        time.sleep(1)
        credits[key] = {"file": os.path.basename(out), "title": title, "license": lic, "author": artist,
                        "page": ii.get("descriptionurl"), "size": [ii.get("width"), ii.get("height")]}
        print("OK", key, lic, ii.get("width"), ii.get("height"))
    json.dump(credits, open(f"{story_dir}/img/credits.json", "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
