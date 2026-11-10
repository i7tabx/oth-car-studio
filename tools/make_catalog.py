#!/usr/bin/env python3
"""Build the site's car/part lists from the files in site/files.

  python tools/make_catalog.py            (run from the site folder)

Reads every .othcar / .othacc in files/, copies each preview to files/previews/,
and writes the lists into index.html (no server or build step needed).
site.json: "download" = app zip URL, "files_base" = where the .othcar/.othacc files are hosted
(e.g. a GitHub release download URL). Empty = files/ next to the page.
"""
import json, os, re, sys, zipfile

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(SITE, "files")
PREV = os.path.join(FILES, "previews")
CATALOG = os.path.join(SITE, "..", "wwwroot", "parts", "catalog.json")
PICKUP = re.compile(r"raptor|sierra|silverado|hilux|f-?150|tundra|ram|tacoma|ranger|gladiator|amarok|navara|pickup|truck", re.I)

def clean(s, n=120):
    return re.sub(r"[\x00-\x1f]", "", str(s or ""))[:n].strip()

def url(cfg, name):
    base = cfg.get("files_base") or "files/"
    return base.rstrip("/") + "/" + name

def main():
    cfg = json.load(open(os.path.join(SITE, "site.json"), encoding="utf-8"))
    os.makedirs(PREV, exist_ok=True)
    cars, parts = [], []
    for fn in sorted(os.listdir(FILES)) if os.path.isdir(FILES) else []:
        path = os.path.join(FILES, fn)
        low = fn.lower()
        if not (low.endswith(".othcar") or low.endswith(".othacc")):
            continue
        try:
            with zipfile.ZipFile(path) as z:
                m = json.loads(z.read("manifest.json").decode("utf-8"))
                stem = re.sub(r"[^a-z0-9_]+", "_", os.path.splitext(low)[0])
                preview = None
                if "preview.png" in z.namelist():
                    with open(os.path.join(PREV, stem + ".png"), "wb") as f:
                        f.write(z.read("preview.png"))
                    preview = "files/previews/" + stem + ".png"
        except Exception as e:
            print("skip", fn, e); continue
        cr = m.get("credit") or {}
        credit = {k: clean(cr.get(k)) for k in ("title", "author", "license", "source")}
        if not credit["license"] or not credit["author"]:
            print("WARNING:", fn, "has no author/license - fix before publishing")
        size = os.path.getsize(path)
        if low.endswith(".othcar") and m.get("format") == "othcar":
            t = m.get("tune") or {}
            name = clean(m.get("name"), 60)
            cars.append({"id": stem, "name": name, "type": "pickup" if PICKUP.search(name) else "suv", "url": url(cfg, fn), "size": size,
                         "preview": preview, "credit": credit, "acc": [a for a in t.get("acc", []) if isinstance(a, str)][:12]})
        elif low.endswith(".othacc") and m.get("format") == "othacc":
            p = m.get("part") or {}
            light = p.get("light") if isinstance(p.get("light"), dict) else None
            parts.append({"id": clean(p.get("id"), 40), "name": clean(p.get("name"), 40), "name_en": clean(p.get("name_en"), 60),
                          "mass_kg": p.get("mass_kg", 0), "cda_m2": p.get("cda_m2", 0), "wading_m": p.get("wading_m", 0),
                          "light": {k: light.get(k) for k in ("lumens", "beam_deg", "kelvin")} if light else None,
                          "url": url(cfg, fn), "size": size, "preview": preview, "credit": credit})
    catalog = json.load(open(CATALOG, encoding="utf-8")) if os.path.exists(CATALOG) else {}
    page = os.path.join(SITE, "index.html")
    html = open(page, encoding="utf-8").read()
    def put(id_, data):
        nonlocal html
        js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        html, n = re.subn(r'(<script id="%s" type="application/json">).*?(</script>)' % id_, lambda mm: mm.group(1) + js + mm.group(2), html, flags=re.S)
        assert n == 1, id_
    put("data-site", {"download": cfg.get("download", ""), "version": cfg.get("version", "")})
    put("data-cars", cars)
    put("data-parts", parts)
    put("data-catalog", catalog)
    open(page, "w", encoding="utf-8").write(html)
    print(f"cars: {len(cars)}  parts: {len(parts)}  built-in parts: {len(catalog.get('parts', []))}")

if __name__ == "__main__":
    main()
