"""Builds src/data.json and img/items.png from the installed Steam game.

    python tools/extract.py [--game "<Legends of Idleon folder>"] [--ru <IdleOn-Rusificator/translation>]

Everything comes from the game files:
  * N.js (inside resources/app.asar): anvil tabs `ItemToCraftNAME`, recipes `ItemToCraftCostTYPE`,
    level/EXP `ItemToCraftEXP`, unlock hints `AnvilRecipeHints`, every item definition (`addNewItem` etc.);
  * lib/default.pak: item icons `assets/data/<ItemId>.png` (72x72), packed into one atlas.
Russian names are optional and come from the IdleOn-Rusificator dictionaries.
If the game was patched by the Rusificator, its untouched backup `app.asar.ru-backup` is read instead.
"""
import argparse, gzip, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
import asar, pak, items as itemdefs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 72
# typeGen groups shown in "My resources"; anything used by a recipe is shown too
RES_TYPES = {"bOre", "bBar", "bLog", "bLeaf", "bCraft", "cOil", "dFish", "dBugs", "dCritters", "dSouls"}


def read_game(game):
    res = os.path.join(game, "resources")
    path = os.path.join(res, "app.asar.ru-backup")
    if not os.path.exists(path):
        path = os.path.join(res, "app.asar")
    header, base = asar.read_header(path)
    want = {"distBuild/static/game/N.js": None, "distBuild/static/game/lib/default.pak": None}
    with open(path, "rb") as f:
        for p, e in asar.walk(header):
            if p in want:
                f.seek(base + int(e["offset"]))
                want[p] = f.read(e["size"])
    print("read", path)
    return want["distBuild/static/game/N.js"].decode("utf-8"), want["distBuild/static/game/lib/default.pak"]


def literal(src, name):
    """Value of the game's `X.<name>=function(){return <literal>}` as Python data.
    The literals are arrays of strings, sometimes written as `"a b c".split(" ")`."""
    m = re.search(r"\." + name + r"=function\(\)\{return", src)
    i, depth, q, start = m.end(), 0, None, m.end()
    while True:
        c = src[i]
        if q:
            if c == "\\":
                i += 1
            elif c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        i += 1
    body = src[start:i]
    body = re.sub(r'("(?:[^"\\]|\\.)*")\.split\(("(?:[^"\\]|\\.)*")\)',
                  lambda mm: json.dumps(json.loads(mm.group(1)).split(json.loads(mm.group(2)))), body)
    return json.loads(body)


def clean(name):
    return name.replace("_", " ").replace("|", " ").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=r"D:\Games\SteamLibrary\steamapps\common\Legends of Idleon")
    ap.add_argument("--ru", default=os.path.join(ROOT, "..", "IdleOn-Rusificator", "translation"))
    a = ap.parse_args()

    njs, pakdata = read_game(a.game)
    names = literal(njs, "ItemToCraftNAME")
    costs = literal(njs, "ItemToCraftCostTYPE")
    exp = literal(njs, "ItemToCraftEXP")
    hints = [h.split(" ") if isinstance(h, str) else h for h in literal(njs, "AnvilRecipeHints")]
    bribe = literal(njs, "BribeDescriptions")[9]  # Fossil_Fuel_Legislation: OilConsume
    defs = itemdefs.parse(njs)
    print(sum(map(len, names)), "recipes in", len(names), "tabs;", len(defs), "item definitions")

    ru_items, ru_text = {}, {}
    if os.path.isdir(a.ru):
        ru_items = json.load(open(os.path.join(a.ru, "items.json"), encoding="utf-8"))
        for f in ("lists.json", "code.json"):
            ru_text.update(json.load(open(os.path.join(a.ru, f), encoding="utf-8")))
    else:
        print("no Russian dictionaries at", a.ru)

    # which items the page needs
    used = set()
    tabs = []
    for t, row in enumerate(names):
        tab = []
        for i, iid in enumerate(row):
            cost = [[c[0], int(float(c[1]))] for c in costs[t][i]]
            used.add(iid)
            used.update(c[0] for c in cost)
            hint = hints[t][i] if t < len(hints) and i < len(hints[t]) else "_"
            tab.append({"id": iid, "lv": int(float(exp[t][i][0])), "xp": int(float(exp[t][i][1])), "cost": cost,
                        "hint": None if hint in ("_", "") else hint})
        tabs.append(tab)
    used.update(k for k, d in defs.items() if d.get("typeGen") in RES_TYPES)
    used.update("EquipmentSmithingTabs%d" % (t + 1) for t in range(len(tabs)))

    # forge: ores -> bars, oils
    ores, oils = {}, {}
    for k, d in defs.items():
        if d.get("typeGen") == "bOre" and d.get("Effect") == "Ore" and (k + "Bar") in defs:
            ores[k] = {"bar": k + "Bar", "per": int(d["Amount"]), "sec": d.get("Cooldown")}
            used.update((k, k + "Bar"))
        if d.get("typeGen") == "cOil":
            oils[k] = {"eff": d.get("Effect"), "amt": d.get("Amount"), "use": d.get("Cooldown")}
            used.add(k)

    # icon atlas
    from PIL import Image
    assets = {e["id"]: e for e in pak.HaxeUnserializer(pak.MANIFEST_RE.search(njs).group(1)).read() if "position" in e}
    order = sorted(i for i in used if ("assets/data/%s.png" % i) in assets)
    cols = 32
    atlas = Image.new("RGBA", (cols * CELL, ((len(order) + cols - 1) // cols) * CELL))
    for n, iid in enumerate(order):
        e = assets["assets/data/%s.png" % iid]
        raw = pakdata[e["position"]:e["position"] + e["length"]]
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        if im.size != (CELL, CELL):
            im.thumbnail((CELL, CELL), Image.NEAREST)
        atlas.paste(im, ((n % cols) * CELL + (CELL - im.width) // 2, (n // cols) * CELL + (CELL - im.height) // 2))
    os.makedirs(os.path.join(ROOT, "img"), exist_ok=True)
    atlas.save(os.path.join(ROOT, "img", "items.png"), optimize=True)
    pos = {iid: n for n, iid in enumerate(order)}
    fav = assets["assets/data/SmithingHammerChisel.png"]
    raw = pakdata[fav["position"]:fav["position"] + fav["length"]]
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    Image.open(io.BytesIO(raw)).convert("RGBA").save(os.path.join(ROOT, "img", "favicon.png"))

    out_items = {}
    for iid in sorted(used):
        d = defs.get(iid)
        if not d and iid not in pos:
            continue
        d = d or {}
        en = d.get("displayName", iid)
        rec = {"en": clean(en), "g": d.get("typeGen", ""), "ty": d.get("Type", "")}
        if en in ru_items:
            rec["ru"] = clean(ru_items[en])
        if iid in pos:
            rec["i"] = pos[iid]
        out_items[iid] = rec

    hint_ru = {h: clean(ru_text[h]) for h in {x["hint"] for t in tabs for x in t if x["hint"]} if h in ru_text}
    build = re.search(r'"buildid"\s+"(\d+)"', open(os.path.join(a.game, "..", "..", "appmanifest_1476970.acf")).read()) \
        if os.path.exists(os.path.join(a.game, "..", "..", "appmanifest_1476970.acf")) else None
    data = {"build": build.group(1) if build else None, "cols": cols, "cell": CELL, "tabs": tabs, "items": out_items,
            "ores": ores, "oils": oils, "oilBribe": float(bribe[5]), "hintRu": hint_ru}
    os.makedirs(os.path.join(ROOT, "src"), exist_ok=True)
    with open(os.path.join(ROOT, "src", "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("src/data.json:", len(out_items), "items;", "img/items.png:", len(order), "icons", atlas.size)


if __name__ == "__main__":
    main()
