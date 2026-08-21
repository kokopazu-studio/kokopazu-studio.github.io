# -*- coding: utf-8 -*-
"""
kokopazu.com static site builder.

  python src/build.py            # full build (pages + media + presskit zip)
  python src/build.py --pages    # pages only (fast)

Inputs : src/facts.json, src/content/{ko,en}.json, src/templates/*, src/static/*, src/media.json
Outputs: repo root (index.html, en/, presskit/, demo/, wishlist/, discord/, 404.html, sitemap.xml, robots.txt,
         site.webmanifest, assets/{css,js,img,video,logo,presskit})
Originals referenced by media.json are only read, never modified.
"""
import os, sys, json, shutil, hashlib, zipfile, datetime, urllib.parse
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape

Image.MAX_IMAGE_PIXELS = None
SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
PAGES_ONLY = "--pages" in sys.argv

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

F = load(os.path.join(SRC, "facts.json"))
KO = load(os.path.join(SRC, "content", "ko.json"))
EN = load(os.path.join(SRC, "content", "en.json"))
MEDIA = load(os.path.join(SRC, "media.json"))
RELEASED = F["release"]["state"] == "released"
STAMP = datetime.date.today().strftime("%Y%m%d")

def write(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("  write", rel, f"{len(text.encode('utf-8'))//1024}KB")

# ---------- link helpers ----------
def utm(url, source, medium, content):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source={source}&utm_medium={medium}&utm_campaign={F['utm']['campaign']}&utm_content={content}"
def steam(content): return utm(F["links"]["steam"], F["utm"]["source"], F["utm"]["medium"], content)
def demo(content): return utm(F["links"]["steam_demo"], F["utm"]["source"], F["utm"]["medium"], content)
def steam_press(content): return utm(F["links"]["steam"], "presskit", "press", content)

# ---------- media ----------
IMG_META = {}   # name -> {"w":..,"h":..,"widths":[..],"jpg_only":bool}

def center_crop(im, aspect):
    if not aspect: return im
    aw, ah = [float(x) for x in aspect.split(":")]
    w, h = im.size
    tw, th = w, int(round(w * ah / aw))
    if th > h:
        th = h; tw = int(round(h * aw / ah))
    l = (w - tw) // 2; t = (h - th) // 2
    return im.crop((l, t, l + tw, t + th))

def build_images():
    out = os.path.join(ROOT, "assets", "img"); os.makedirs(out, exist_ok=True)
    for name, spec in MEDIA["images"].items():
        src = spec["src"]
        im = Image.open(src)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGBA", im.size, (27, 20, 16, 255)); bg.alpha_composite(im.convert("RGBA")); im = bg.convert("RGB")
        else:
            im = im.convert("RGB")
        if spec.get("crop"):
            l, t, r, b = spec["crop"]; w, h = im.size
            im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
        im = center_crop(im, spec.get("aspect"))
        widths = sorted({min(w, im.width) for w in spec["widths"]}, reverse=True)
        for w in widths:
            r = im.resize((w, int(round(im.height * w / im.width))), Image.LANCZOS)
            if not spec.get("jpg_only"):
                r.save(os.path.join(out, f"{name}-{w}.webp"), "WEBP", quality=80, method=6)
            r.save(os.path.join(out, f"{name}-{w}.jpg"), "JPEG", quality=82, optimize=True, progressive=True)
        big = widths[0]
        IMG_META[name] = {"w": big, "h": int(round(im.height * big / im.width)), "widths": widths, "jpg_only": bool(spec.get("jpg_only"))}
    with open(os.path.join(SRC, "img_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(IMG_META, fh, indent=1)
    print(f"  images: {len(MEDIA['images'])} processed")

def build_videos():
    out = os.path.join(ROOT, "assets", "video"); os.makedirs(out, exist_ok=True)
    for name, src in MEDIA["videos"].items():
        dst = os.path.join(out, f"{name}.mp4")
        shutil.copyfile(src, dst)
    print(f"  videos: {len(MEDIA['videos'])} copied")

def build_logos():
    out = os.path.join(ROOT, "assets", "logo"); os.makedirs(out, exist_ok=True)
    for name, src in MEDIA["logos"].items():
        im = Image.open(src).convert("RGBA")
        bbox = im.getchannel("A").getbbox()
        if bbox: im = im.crop(bbox)
        if im.width > 1600:
            im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
        im.save(os.path.join(out, f"{name}.png"), "PNG", optimize=True)
        # lightweight web variants (PNG stays as the download/fallback copy)
        im.save(os.path.join(out, f"{name}.webp"), "WEBP", quality=90, method=6)
        if name == "studio-mark":
            im.resize((96, 96), Image.LANCZOS).save(os.path.join(out, "studio-mark-96.png"), "PNG", optimize=True)
    print(f"  logos: {len(MEDIA['logos'])} written")

def build_presskit_media():
    out = os.path.join(ROOT, "assets", "presskit"); thumbs = os.path.join(out, "thumbs")
    os.makedirs(thumbs, exist_ok=True)
    items = []
    for group in ("keyart", "screenshots"):
        for it in MEDIA["presskit"][group]:
            im = Image.open(it["src"])
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGBA", im.size, (27, 20, 16, 255)); bg.alpha_composite(im.convert("RGBA")); im = bg.convert("RGB")
            else:
                im = im.convert("RGB")
            mw = it.get("max_width", 1920)
            if im.width > mw: im = im.resize((mw, int(im.height * mw / im.width)), Image.LANCZOS)
            im.save(os.path.join(out, it["file"]), "JPEG", quality=88, optimize=True, progressive=True)
            th = center_crop(im, "16:9"); th = th.resize((640, 360), Image.LANCZOS)
            thumb = os.path.splitext(it["file"])[0] + "-thumb.jpg"
            th.save(os.path.join(thumbs, thumb), "JPEG", quality=78, optimize=True)
            items.append((group, {"label": it["label"], "file": it["file"], "thumb": thumb}))
    print("  presskit media:", len(items))
    return [i for g, i in items if g == "keyart"], [i for g, i in items if g == "screenshots"]

def build_presskit_zip(keyart, shots, factsheet_txt):
    zpath = os.path.join(ROOT, "presskit", "presskit-save-princess-torosso.zip")
    os.makedirs(os.path.dirname(zpath), exist_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("factsheet.txt", factsheet_txt)
        for name in MEDIA["logos"]:
            z.write(os.path.join(ROOT, "assets", "logo", f"{name}.png"), f"logos/{name}.png")
        for it in keyart: z.write(os.path.join(ROOT, "assets", "presskit", it["file"]), f"keyart/{it['file']}")
        for it in shots: z.write(os.path.join(ROOT, "assets", "presskit", it["file"]), f"screenshots/{it['file']}")
    size = os.path.getsize(zpath)
    print(f"  presskit zip: {size//1024//1024}MB")
    assert size < 50 * 1024 * 1024, "presskit zip must stay under 50MB"

def copy_static():
    for sub in ("css", "js", "fonts"):
        s = os.path.join(SRC, "static", sub)
        if not os.path.isdir(s): continue
        d = os.path.join(ROOT, "assets", sub); os.makedirs(d, exist_ok=True)
        for fn in os.listdir(s):
            shutil.copyfile(os.path.join(s, fn), os.path.join(d, fn))
    print("  static: css/js/fonts copied")

# ---------- templates ----------
env = Environment(loader=FileSystemLoader(os.path.join(SRC, "templates")), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

ICON_STEAM = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 1 0 9.95 11H14.5a3 3 0 1 1-.3-3.3l3.1-2.1A7 7 0 1 0 19 12h3A10 10 0 0 0 12 2Z"/></svg>'
ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>'

def img_tag(name, alt, sizes):
    m = IMG_META.get(name)
    if not m:
        return f'<img src="/assets/img/{name}-1280.jpg" alt="{alt}" loading="lazy" decoding="async">'
    widths = m["widths"]
    jpg_set = ", ".join(f"/assets/img/{name}-{w}.jpg {w}w" for w in widths)
    webp_set = ", ".join(f"/assets/img/{name}-{w}.webp {w}w" for w in widths)
    src = f"/assets/img/{name}-{widths[0]}.jpg"
    alt_e = alt.replace('"', "&quot;")
    pic = "<picture>"
    if not m["jpg_only"]:
        pic += f'<source type="image/webp" srcset="{webp_set}" sizes="{sizes}">'
    pic += f'<img src="{src}" srcset="{jpg_set}" sizes="{sizes}" width="{m["w"]}" height="{m["h"]}" alt="{alt_e}" loading="lazy" decoding="async"></picture>'
    return pic

from markupsafe import Markup
env.globals.update(steam=steam, demo=demo, steam_press=steam_press, img=lambda n, a, s: Markup(img_tag(n, a, s)))

def languages_list(lang):
    return ", ".join(l[lang] for l in F["languages"]["list"])

def jsonld(lang):
    c = KO if lang == "ko" else EN
    org = {"@context": "https://schema.org", "@type": "Organization", "name": F["studio"]["name_en"], "alternateName": F["studio"]["name_ko"],
           "url": F["links"]["site"] + "/", "email": F["studio"]["email"], "foundingDate": F["studio"]["founded"],
           "description": ("판타지 3D 액션 어드벤처 Save Princess Torosso를 개발하는 1인 인디 게임 스튜디오" if lang == "ko" else "Solo indie studio developing the fantasy 3D action adventure Save Princess Torosso"),
           "sameAs": [F["links"]["facebook"], F["links"]["x"], F["links"]["youtube"], F["links"]["discord_en"], F["links"]["discord_ko"], F["links"]["steam"]]}
    game = {"@context": "https://schema.org", "@type": "VideoGame", "name": F["game"]["title"], "url": F["links"]["site"] + ("/" if lang == "ko" else "/en/"),
            "description": F["seo"]["description_" + lang], "genre": ["Fantasy", "Action", "Adventure", "Platformer"],
            "gamePlatform": "PC (Windows)", "operatingSystem": F["min_spec"]["os"], "applicationCategory": "Game",
            "inLanguage": [l["code"] for l in F["languages"]["list"]], "gameEngine": F["game"]["engine"],
            "author": {"@type": "Organization", "name": F["studio"]["name_en"]}, "publisher": {"@type": "Organization", "name": F["studio"]["name_en"]},
            "sameAs": [F["links"]["steam"]]}
    if RELEASED: game["datePublished"] = F["release"].get("exact_pdt") or F["release"]["display_iso"]
    else: game["releaseNotes"] = ("2026년 11월 Steam 출시 예정, 데모 플레이 가능" if lang == "ko" else "Coming to Steam in November 2026. Free demo available now.")
    if F["price"]["show"]:
        game["offers"] = {"@type": "Offer", "price": str(F["price"]["usd"]), "priceCurrency": "USD", "url": F["links"]["steam"],
                          "availability": "https://schema.org/InStock" if RELEASED else "https://schema.org/PreOrder"}
    return json.dumps([org, game], ensure_ascii=False)

def render_index(lang):
    c = KO if lang == "ko" else EN
    t = env.get_template("index.html")
    html = t.render(f=F, c=c, ko=KO, en=EN, released=RELEASED, build_stamp=STAMP,
                    page_kind="index", page_title=F["seo"]["title_" + lang], page_description=F["seo"]["description_" + lang],
                    og_description=(F["seo"]["description_" + lang]), canonical=F["seo"]["canonical_" + lang],
                    alt_ko=F["seo"]["canonical_ko"], alt_en=F["seo"]["canonical_en"], home_url=("/" if lang == "ko" else "/en/"),
                    jsonld=jsonld(lang), languages_list=languages_list(lang), icon_steam=ICON_STEAM, icon_play=ICON_PLAY, body_class="")
    write("index.html" if lang == "ko" else "en/index.html", html)

def render_presskit(keyart, shots):
    t = env.get_template("presskit.html")
    c = dict(EN); c["lang"] = "en"; c["html_lang"] = "en"; c["other_lang"] = "ko"; c["other_lang_url"] = "/presskit/?lang=ko"; c["lang_banner"] = KO["lang_banner"]
    html = t.render(f=F, c=c, ko=KO, en=EN, released=RELEASED, build_stamp=STAMP,
                    page_kind="presskit", page_title="Presskit — Save Princess Torosso | Kokopazu Studio",
                    page_description="Press kit for Save Princess Torosso: factsheet, description, screenshots, logos, press release and contact.",
                    og_description="Press kit for Save Princess Torosso — factsheet, screenshots, logos and contact.",
                    canonical=F["links"]["presskit"], alt_ko=None, alt_en=None, home_url="/",
                    jsonld=jsonld("en"), languages_list_en=languages_list("en"), languages_list_ko=languages_list("ko"),
                    presskit_keyart=keyart, presskit_shots=shots, icon_steam=ICON_STEAM, icon_play=ICON_PLAY, body_class="page-presskit")
    write("presskit/index.html", html)

def render_redirects():
    t = env.get_template("redirect.html")
    targets = {"demo": demo("shortlink_demo"), "wishlist": steam("shortlink_wishlist"), "discord": F["links"]["discord_en"], "discord/ko": F["links"]["discord_ko"]}
    for path, target in targets.items():
        write(f"{path}/index.html", t.render(title="Redirect — Kokopazu Studio", target=target, ko=KO, en=EN))

def render_404():
    write("404.html", env.get_template("404.html").render(ko=KO, en=EN))

def write_meta_files():
    today = datetime.date.today().isoformat()
    site = F["links"]["site"]
    urls = [("/", "weekly", "1.0"), ("/en/", "weekly", "1.0"), ("/presskit/", "monthly", "0.6")]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    for u, cf, pr in urls:
        sm += f"  <url>\n    <loc>{site}{u}</loc>\n"
        if u in ("/", "/en/"):
            sm += f'    <xhtml:link rel="alternate" hreflang="ko" href="{site}/"/>\n    <xhtml:link rel="alternate" hreflang="en" href="{site}/en/"/>\n    <xhtml:link rel="alternate" hreflang="x-default" href="{site}/en/"/>\n'
        sm += f"    <lastmod>{today}</lastmod>\n    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>\n"
    sm += "</urlset>\n"
    write("sitemap.xml", sm)
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /demo/\nDisallow: /wishlist/\nDisallow: /discord/\n\nSitemap: {site}/sitemap.xml\n")
    write("site.webmanifest", json.dumps({"name": F["studio"]["name_en"], "short_name": "Kokopazu", "icons": [{"src": "/favicon-192.png", "sizes": "192x192", "type": "image/png"}],
                                          "theme_color": "#0b0908", "background_color": "#0b0908", "display": "browser", "start_url": "/"}, ensure_ascii=False, indent=2))
    open(os.path.join(ROOT, ".nojekyll"), "a").close()

def factsheet_text():
    L = [f"{F['game']['title']} — Factsheet", "",
         f"Developer: {F['studio']['name_en']} (solo indie studio, {F['studio']['country_en']})",
         f"Genre: {F['game']['genre_en']}", f"Platform: {F['platforms']['display_en']}",
         f"Release: {('Released' if RELEASED else F['release']['display_en'] + ' (planned)')}", "Demo: Available now on Steam",
         f"Price: {F['price']['display']}" if F["price"]["show"] else "", f"Languages ({F['languages']['count']}): {languages_list('en')}",
         f"Controls: {EN['hero']['meta_controls']}", f"Engine: {F['game']['engine']}",
         f"Steam: {F['links']['steam']}", f"Website: {F['links']['site']}", f"Email: {F['studio']['email']}",
         f"Discord (EN): {F['links']['discord_en']}", f"Discord (KO): {F['links']['discord_ko']}",
         f"YouTube: {F['links']['youtube']}", f"X: {F['links']['x']}", f"Facebook: {F['links']['facebook']}", "",
         "About", EN["hero"]["hook"] + " " + EN["hero"]["sub_1"] + " " + EN["hero"]["sub_2"], EN["loop"]["lead"], EN["magic"]["lead"], EN["traverse"]["lead"], EN["leaderboard"]["body"], "",
         "Story", *EN["story"]["p"], "", "Images and media may be used for editorial and promotional purposes with credit to Kokopazu Studio."]
    return "\n".join(x for x in L if x is not None)

def main():
    print("== kokopazu.com build ==")
    if not PAGES_ONLY:
        build_images(); build_videos(); build_logos()
        keyart, shots = build_presskit_media()
    else:
        # reuse existing outputs; image meta saved by the last full build
        meta_path = os.path.join(SRC, "img_meta.json")
        if not os.path.exists(meta_path):
            sys.exit("img_meta.json missing — run a full build first (python src/build.py)")
        IMG_META.update(load(meta_path))
        keyart = [{"label": i["label"], "file": i["file"], "thumb": os.path.splitext(i["file"])[0] + "-thumb.jpg"} for i in MEDIA["presskit"]["keyart"]]
        shots = [{"label": i["label"], "file": i["file"], "thumb": os.path.splitext(i["file"])[0] + "-thumb.jpg"} for i in MEDIA["presskit"]["screenshots"]]
    copy_static()
    render_index("ko"); render_index("en"); render_presskit(keyart, shots); render_redirects(); render_404(); write_meta_files()
    if not PAGES_ONLY:
        build_presskit_zip(keyart, shots, factsheet_text())
    write("presskit/factsheet.txt", factsheet_text())
    print("== done ==")

if __name__ == "__main__":
    main()
