"""Pre-render every ARVAELLE page into static HTML for Google, Bing and AI crawlers.

Usage:  python3 build.py            (needs: pip install playwright; a Chrome/Chromium)
Output: public/  (Vercel serves this folder)

Edit SITE below once the final domain is live.
"""
import asyncio, html, json, os, re, shutil, subprocess, sys, time, datetime
from playwright.async_api import async_playwright

SITE = os.environ.get("SITE_URL", "https://arvaelle.vercel.app").rstrip("/")
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.join(ROOT, "src"), os.path.join(ROOT, "public")
PORT = 8765
CHROME = os.environ.get("CHROME_PATH", "/usr/bin/google-chrome")
TODAY = datetime.date.today().isoformat()
INDEXNOW_KEY = "a7f3c9e2b1d84f6e9c0a5b3d2e1f4a6c"


def path_for(key, data):
    if key == "":
        return "/"
    if key in data["products"]:
        return f"/products/{key}/"
    if key.startswith("c-"):
        return f"/{key[2:]}/"
    if key.startswith("journal-"):
        return f"/journal/{key[8:]}/"
    return f"/{key}/"


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


STORE = {
    "@type": "JewelryStore", "@id": f"{SITE}/#store", "name": "ARVAELLE", "url": f"{SITE}/",
    "description": "ARVAELLE is a Dubai-based online jewellery store selling gold-plated necklaces and gift sets. Every piece arrives in a signature black gift box with a handwritten card. Orders are taken on WhatsApp and delivered across Dubai, same day for orders paid before 2 pm.",
    "slogan": "Timeless jewelry for modern souls", "image": f"{SITE}/img/sol-main.jpg",
    "telephone": "+971541787801", "priceRange": "AED 229–429", "currenciesAccepted": "AED",
    "paymentAccepted": "Credit Card, Debit Card, Apple Pay, Aani",
    "address": {"@type": "PostalAddress", "addressLocality": "Dubai", "addressCountry": "AE"},
    "areaServed": [{"@type": "City", "name": "Dubai"}, {"@type": "Country", "name": "United Arab Emirates"}],
    "contactPoint": {"@type": "ContactPoint", "contactType": "sales", "telephone": "+971541787801", "availableLanguage": ["English", "Arabic"]},
}
RETURN_POLICY = {"@type": "MerchantReturnPolicy", "applicableCountry": "AE", "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                 "merchantReturnDays": 7, "returnMethod": "https://schema.org/ReturnByMail", "returnFees": "https://schema.org/ReturnShippingFees"}
SHIPPING = {"@type": "OfferShippingDetails", "shippingRate": {"@type": "MonetaryAmount", "value": 25, "currency": "AED"},
            "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "AE", "addressRegion": "Dubai"},
            "deliveryTime": {"@type": "ShippingDeliveryTime",
                             "handlingTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 0, "unitCode": "DAY"},
                             "transitTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY"}}}


def product_ld(p, url):
    return {"@type": "Product", "@id": url + "#product", "name": p["name"], "sku": "ARV-" + p["id"].upper(),
            "brand": {"@type": "Brand", "name": "ARVAELLE"}, "description": p["desc"], "material": "Gold-plated", "color": "Gold",
            "image": [SITE + i for i in p["images"]], "url": url,
            "offers": {"@type": "Offer", "url": url, "priceCurrency": "AED", "price": str(p["price"]),
                       "availability": "https://schema.org/InStock", "itemCondition": "https://schema.org/NewCondition",
                       "seller": {"@id": f"{SITE}/#store"}, "shippingDetails": SHIPPING, "hasMerchantReturnPolicy": RETURN_POLICY}}


def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def faq_ld(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}


async def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(SRC, "img"), os.path.join(OUT, "img"))
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "-d", SRC],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    urls = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path=CHROME)
            ctx = await browser.new_context(viewport={"width": 1366, "height": 900})
            await ctx.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"), lambda r: r.abort())
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://localhost:{PORT}/template.html")
            data = await page.evaluate("""() => ({
              products: Object.fromEntries(PRODUCTS.map(p=>[p.id,{id:p.id,name:p.name.en,desc:p.desc.en,price:p.price,images:p.images.map(i=>i[0])}])),
              cats: CATS.map(c=>({id:c.id,tag:c.tag,name:c.name.en})),
              pages: Object.fromEntries(Object.entries(PAGES).map(([k,v])=>[k,{title:v.t.en,parent:v.parent||null}]))
            })""")
            keys = [""] + list(data["products"]) + ["c-" + c["id"] for c in data["cats"]] + list(data["pages"])
            for key in keys:
                await page.add_init_script(f"window.__ROUTE__={json.dumps(key)}; try{{localStorage.clear()}}catch(e){{}}")
                await page.goto(f"http://localhost:{PORT}/template.html")
                await page.wait_for_timeout(250)
                info = await page.evaluate("""() => {
                  const scope = document.body.classList.contains('page') ? '#pgBody' : (['pdp','coll'].some(c=>document.body.classList.contains(c)) ? null : '#faq');
                  const faqs = scope ? [...document.querySelectorAll(scope+' details')].map(d=>[d.querySelector('summary').textContent.trim(), d.querySelector('p').textContent.trim()]) : [];
                  const grid = [...document.querySelectorAll(document.body.classList.contains('coll') ? '#grid .card a[href^="/products/"]' : '#pgBody .card a[href^="/products/"]')].map(a=>a.getAttribute('href'));
                  return {title: document.title, desc: document.querySelector('meta[name=description]').content, faqs, grid: [...new Set(grid)]};
                }""")
                doc = await page.content()
                url = SITE + path_for(key, data)
                graph = [STORE, {"@type": "WebSite", "@id": f"{SITE}/#website", "name": "ARVAELLE", "url": f"{SITE}/", "publisher": {"@id": f"{SITE}/#store"}}]
                image = f"{SITE}/img/sol-main.jpg"
                if key in data["products"]:
                    p = data["products"][key]
                    graph.append(product_ld(p, url))
                    image = SITE + p["images"][0]
                    graph.append(crumbs([("Home", SITE + "/"), (p["name"], url)]))
                elif key.startswith("c-"):
                    c = next(c for c in data["cats"] if c["id"] == key[2:])
                    graph.append({"@type": "CollectionPage", "name": c["name"], "url": url, "description": info["desc"],
                                  "mainEntity": {"@type": "ItemList", "itemListElement": [
                                      {"@type": "ListItem", "position": i + 1, "url": SITE + h} for i, h in enumerate(info["grid"])]}})
                    graph.append(crumbs([("Home", SITE + "/"), (c["name"], url)]))
                elif key:
                    pg = data["pages"][key]
                    trail = [("Home", SITE + "/")]
                    if pg["parent"]:
                        trail.append((data["pages"][pg["parent"]]["title"], SITE + path_for(pg["parent"], data)))
                    trail.append((pg["title"], url))
                    graph.append({"@type": "Article" if key.startswith("journal-") else "WebPage", "headline" if key.startswith("journal-") else "name": pg["title"],
                                  "url": url, "description": info["desc"], "inLanguage": "en-AE", "dateModified": TODAY,
                                  **({"author": {"@id": f"{SITE}/#store"}, "publisher": {"@id": f"{SITE}/#store"}, "image": image} if key.startswith("journal-") else {})})
                    graph.append(crumbs(trail))
                    for h in info["grid"]:
                        pk = h.strip("/").split("/")[-1]
                        if pk in data["products"]:
                            graph.append(product_ld(data["products"][pk], SITE + h))
                else:
                    graph += [product_ld(p, SITE + path_for(k, data)) for k, p in data["products"].items()]
                if info["faqs"]:
                    graph.append(faq_ld(info["faqs"]))

                t, d = html.escape(info["title"]), html.escape(info["desc"])
                head = (f'<link rel="canonical" href="{url}">\n<link rel="alternate" hreflang="en-ae" href="{url}">\n'
                        f'<link rel="alternate" hreflang="x-default" href="{url}">\n'
                        f'<meta property="og:url" content="{url}">\n<meta property="og:image" content="{image}">\n'
                        f'<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">\n'
                        f'<script>window.__ROUTE__={json.dumps(key)};</script>\n' + ld({"@context": "https://schema.org", "@graph": graph}))
                doc = re.sub(r'<link rel="canonical"[^>]*>\s*', "", doc)
                doc = re.sub(r'<link rel="alternate" hreflang[^>]*>\s*', "", doc)
                doc = re.sub(r'<meta property="og:(title|description|url|image)"[^>]*>\s*', "", doc)
                doc = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", doc, flags=re.S)
                doc = doc.replace("</head>", head + "\n</head>", 1)
                dest = os.path.join(OUT, path_for(key, data).strip("/"), "index.html")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write("<!DOCTYPE html>\n" + doc.split(">", 1)[1] if doc.lower().startswith("<!doctype") else "<!DOCTYPE html>\n" + doc)
                urls.append((url, "1.0" if key == "" else "0.8" if key in data["products"] or key.startswith("c-") else "0.6"))
                print("built", path_for(key, data))
            await browser.close()
            if errors:
                print("JS ERRORS:", errors)
                sys.exit(1)
    finally:
        server.terminate()

    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u, pr in urls:
            f.write(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod><priority>{pr}</priority></url>\n")
        f.write("</urlset>\n")
    bots = ["OAI-SearchBot", "ChatGPT-User", "GPTBot", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot",
            "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended"]
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + "User-agent: *\nAllow: /\n\n" + f"Sitemap: {SITE}/sitemap.xml\n")
    with open(os.path.join(OUT, f"{INDEXNOW_KEY}.txt"), "w") as f:
        f.write(INDEXNOW_KEY)
    shutil.copy(os.path.join(SRC, "llms.txt"), os.path.join(OUT, "llms.txt"))
    with open(os.path.join(OUT, "llms.txt"), "a") as f:
        f.write("\n## Pages\n" + "".join(f"- {u}\n" for u, _ in urls))
    with open(os.path.join(OUT, "urls.txt"), "w") as f:
        f.write("\n".join(u for u, _ in urls) + "\n")
    print(f"\n{len(urls)} pages built for {SITE}")


asyncio.run(main())
