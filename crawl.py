#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cao gia xe dap cho XDGK PriceWatch.

XDGK la danh muc goc: lay URL san pham tu product sitemap, mo tung trang san
pham de lay gia + ton kho. Cac doi thu hien van cao trang danh sach de giu
workflow nhe, sau nay co the them sitemap rieng tung nguon.
"""
import concurrent.futures
import gzip
import html as html_lib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SOURCES = [
  {"id":"xdgk","name":"Xe Đạp Giá Kho","region":"me","url":"https://xedapgiakho.com/","base":"https://xedapgiakho.com","me":True,"mode":"xdgk_sitemap","sitemap":"https://xedapgiakho.com/sitemap_index.xml"},
  {"id":"hanoibike","name":"Hanoibike","region":"bac","url":"https://hanoibike.net/","base":"https://hanoibike.net","me":False},
  {"id":"xedapdanang","name":"XĐ Đà Nẵng – Đức Liên","region":"trung","url":"https://xedapdanang.vn/","base":"https://xedapdanang.vn","me":False},
  {"id":"xedapthegioi","name":"Xe Đạp Thế Giới","region":"nam","url":"https://xedapthegioi.vn/","base":"https://xedapthegioi.vn","me":False},
]

HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gia-lich-su.json")
UA = {
    "User-Agent":"Mozilla/5.0 (compatible; XDGK-PriceWatch/1.0)",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding":"gzip",
}
PRICE_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|VND|&#8363;)", re.I)
LINK_RE  = re.compile(r"/(?:products|product|san-pham)/[^\"'#?\s]+")
LOC_RE = re.compile(r"<loc>\s*([^<]+?)\s*</loc>", re.I)

BRANDS = [
    "Giant","Sava","Java","Trinx","Twitter","Hector","Califa","Calli","Fornix",
    "Papylus","Miamor","Raccoon","Jazz Bear","Thống Nhất","Foxy","Levi",
    "Azi","Action","Nijia","Phoenix","Kawamura","Magicbros","Makelen",
    "Bianchi","Kespor","Fortina","Chevaux","California","Galaxy","Life",
    "Nesto","Merida","Louis Garneau","Maruishi","DTFLY","Inveter",
]

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
        charset = res.headers.get_content_charset() or "utf-8"
        encoding = (res.headers.get("Content-Encoding") or "").lower()
    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode(charset, errors="replace")

def num(s):
    return int(re.sub(r"[^\d]","",html_lib.unescape(s or "")))

def clean_text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html_lib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def normalize_url(url):
    url = html_lib.unescape(url or "").strip()
    url = url.split("#")[0].split("?")[0].rstrip("/")
    return url

def meta_content(page, key, attr="name"):
    pat = rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)["\']'
    m = re.search(pat, page, re.I)
    if not m:
        pat = rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+{attr}=["\']{re.escape(key)}["\']'
        m = re.search(pat, page, re.I)
    return clean_text(m.group(1)) if m else ""

def price_from_text(text):
    prices = [num(x) for x in PRICE_RE.findall(text or "")]
    prices = [p for p in prices if 100000 <= p <= 200000000]
    return min(prices) if prices else None

def infer_brand(name):
    plain = (name or "").lower()
    for brand in sorted(BRANDS, key=len, reverse=True):
        if brand.lower() in plain:
            return brand
    return ""

def infer_category(name):
    n = (name or "").lower()
    if "điện" in n or "dien" in n or "xe máy điện" in n:
        return "Xe điện"
    if "trẻ em" in n or "tre em" in n or "bé " in n:
        return "Trẻ em"
    if "đua" in n or "road" in n:
        return "Xe đạp đua"
    if "địa hình" in n or "dia hinh" in n or "mtb" in n:
        return "MTB"
    if "touring" in n or "đường phố" in n or "thành phố" in n:
        return "Touring/City"
    if "gấp" in n or "gap" in n:
        return "Xe gấp"
    if "nữ" in n or "nu " in n:
        return "Xe nữ"
    return "Khác"

class Prod(HTMLParser):
    """Gom text + link + alt theo tung khoi san pham tren trang danh sach."""
    def __init__(self, base):
        super().__init__(); self.base=base
        self.chunks=[]; self.in_del=0; self.skip=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ("script","style"): self.skip+=1
        if tag=="del": self.in_del+=1
        if tag=="a":
            href=a.get("href") or ""
            m=LINK_RE.search(href)
            if m:
                url = href if href.startswith("http") else self.base+m.group(0)
                if url.startswith(self.base):
                    self.chunks.append(("link", normalize_url(url)))
        if tag=="img":
            alt=(a.get("alt") or "").strip()
            if 3<=len(alt)<=120: self.chunks.append(("alt",clean_text(alt)))
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self, tag):
        if tag in ("script","style"): self.skip=max(0,self.skip-1)
        if tag=="del": self.in_del=max(0,self.in_del-1)
    def handle_data(self, d):
        if self.skip: return
        d=clean_text(d)
        if d: self.chunks.append(("deltext" if self.in_del else "text", d))

def parse_listing(page, src):
    p=Prod(src["base"]); p.feed(page)
    ch=p.chunks
    anchors=[i for i,(k,v) in enumerate(ch) if k=="link"]
    segs=[]
    for i in anchors:
        url=ch[i][1]
        if segs and segs[-1][0]==url: segs[-1]=(url,segs[-1][1],i); continue
        segs.append((url,i,i))
    items={}; order=[]
    for si,(url,start,endi) in enumerate(segs):
        prev_end = segs[si-1][2] if si>0 else -1
        next_start = segs[si+1][1] if si+1<len(segs) else len(ch)
        slug=url.rstrip("/").split("/")[-1]
        slug_tok=set(re.split(r"[-_]+",slug.lower()))
        cands=[ch[j][1] for j in range(prev_end+1,min(next_start,len(ch))) if ch[j][0]=="alt"]
        def overlap(a):
            t=set(re.split(r"[^0-9a-zà-ỹ]+",a.lower()))
            return len(t&slug_tok)
        name=max(cands,key=overlap) if cands and max(map(overlap,cands))>=2 else None
        if not name:
            name=re.sub(r"[-_]+"," ",slug).title()
        texts=[v for k,v in ch[endi+1:next_start] if k=="text"]
        blob=" ".join(texts)[:700]
        m=re.search(r"hiện tại[^0-9]{0,30}(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|VND)", blob, re.I)
        price=num(m.group(1)) if m else price_from_text(blob)
        if price and url not in items:
            items[url]={
                "name":name,"price":price,"slug":slug,"brand":infer_brand(name),
                "category":infer_category(name),"stock":"unknown","active":True
            }
            order.append(url)
    return [{"url":u,**items[u]} for u in order]

def sitemap_locs(xml):
    return [html_lib.unescape(x.strip()) for x in LOC_RE.findall(xml or "")]

def discover_product_urls(src):
    index = fetch(src["sitemap"], timeout=45)
    product_maps = [u for u in sitemap_locs(index) if re.search(r"/product-sitemap\d+\.xml$", u)]
    urls=[]
    for sm in product_maps:
        try:
            urls.extend(u for u in sitemap_locs(fetch(sm, timeout=45)) if "/product/" in u)
        except Exception as e:
            print(f"WARN sitemap {sm}: {e}", file=sys.stderr)
    seen=set(); out=[]
    for u in urls:
        u=normalize_url(u)
        if u and u not in seen:
            seen.add(u); out.append(u)
    limit = int(os.getenv("MAX_XDGK_PRODUCTS", "1200"))
    return out[:limit]

def parse_xdgk_product(url):
    page = fetch(url, timeout=45)
    name = (
        meta_content(page, "og:title", "property")
        or meta_content(page, "twitter:title")
        or clean_text(re.search(r"<title[^>]*>(.*?)</title>", page, re.I|re.S).group(1) if re.search(r"<title[^>]*>(.*?)</title>", page, re.I|re.S) else "")
    )
    name = re.sub(r"\s+[-|]\s+Xe Đạp Giá Kho.*$", "", name).strip()
    price = price_from_text(meta_content(page, "twitter:data1"))
    if not price:
        price = price_from_text(page[:80000])
    availability = meta_content(page, "product:availability", "property").lower()
    stock_label = meta_content(page, "twitter:data2").lower()
    explicit_out = any(x in availability + " " + stock_label for x in ("outofstock","out of stock","hết hàng","het hang"))
    in_stock = ("instock" in availability) or ("còn hàng" in stock_label) or ("con hang" in stock_label)
    if explicit_out or not price or not name:
        return None
    sku = meta_content(page, "product:retailer_item_id", "property")
    brand = infer_brand(name)
    return {
        "url": normalize_url(url),
        "name": name,
        "price": price,
        "brand": brand,
        "category": infer_category(name),
        "stock": "instock" if in_stock else "unknown",
        "sku": sku,
        "active": True,
    }

def crawl_xdgk(src):
    urls = discover_product_urls(src)
    print(f"INFO {src['name']}: tim thay {len(urls)} URL san pham trong sitemap")
    workers = max(1, min(12, int(os.getenv("XDGK_CRAWL_WORKERS", "6"))))
    items=[]; errors=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(parse_xdgk_product,u):u for u in urls}
        for i,fut in enumerate(concurrent.futures.as_completed(futs),1):
            try:
                it=fut.result()
                if it: items.append(it)
            except Exception as e:
                errors += 1
                if errors <= 20:
                    print(f"WARN product {futs[fut]}: {e}", file=sys.stderr)
            if i % 100 == 0:
                print(f"INFO {src['name']}: da xu ly {i}/{len(urls)}, hop le {len(items)}")
    items.sort(key=lambda x: x["name"].lower())
    print(f"INFO {src['name']}: bo qua {errors} URL loi")
    return items

def mark_source_inactive(hist, src):
    for rec in hist.get("items",{}).values():
        if rec.get("seller")==src["name"]:
            rec["active"]=False

def apply_items(hist, src, items, t):
    changed=0
    mark_source_inactive(hist, src)
    for it in items:
        rec=hist["items"].setdefault(it["url"],{
            "name":it["name"],"seller":src["name"],"region":src["region"],
            "me":src["me"],"hist":[],"seen":t
        })
        rec["name"]=it["name"]; rec["seller"]=src["name"]; rec["region"]=src["region"]
        rec["me"]=src["me"]; rec["seen"]=t; rec["active"]=True
        for key in ("brand","category","stock","sku"):
            if it.get(key): rec[key]=it[key]
        h=rec.setdefault("hist",[])
        if not h or h[-1]["p"]!=it["price"]:
            if h: changed+=1
            h.append({"t":t,"p":it["price"]})
        rec["hist"]=h[-200:]
    return changed

def main():
    hist={"runs":[],"items":{}}
    if os.path.exists(HIST):
        try:
            with open(HIST,encoding="utf-8") as f:
                hist=json.load(f)
        except Exception:
            pass
    if not isinstance(hist.get("runs"),list): hist["runs"]=[]
    if not isinstance(hist.get("items"),dict): hist["items"]={}
    t=int(time.time()*1000); total=0; changed=0
    for src in SOURCES:
        try:
            if src.get("mode")=="xdgk_sitemap":
                items=crawl_xdgk(src)
            else:
                items=parse_listing(fetch(src["url"]), src)
            if not items: raise RuntimeError("khong tim thay gia")
            changed += apply_items(hist, src, items, t)
            total += len(items)
            print(f"OK  {src['name']}: {len(items)} SP")
        except Exception as e:
            print(f"ERR {src['name']}: {e}", file=sys.stderr)
    if total==0:
        print("ERR Khong cao duoc san pham nao, giu nguyen gia-lich-su.json", file=sys.stderr)
        return 1
    hist["runs"]=(hist.get("runs") or [])[-499:]+[{"t":t,"total":total,"changed":changed}]
    tmp=HIST+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(hist,f,ensure_ascii=False,separators=(",",":"))
        f.write("\n")
    os.replace(tmp,HIST)
    print(f"Tong: {total} SP active, {changed} thay doi gia. Luu: {HIST}")
    return 0

if __name__=="__main__": sys.exit(main())
