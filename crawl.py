#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cào giá xe đạp cho XDGK PriceWatch — chạy bởi GitHub Actions (hoặc tay: python3 crawl.py)
Xuất/ cập nhật gia-lich-su.json cùng định dạng với dashboard."""
import json, re, sys, time, os, urllib.request
from html.parser import HTMLParser

SOURCES = [
  {"id":"xdgk","name":"Xe Đạp Giá Kho","region":"me","url":"https://xedapgiakho.com/","base":"https://xedapgiakho.com","me":True},
  {"id":"hanoibike","name":"Hanoibike","region":"bac","url":"https://hanoibike.net/","base":"https://hanoibike.net","me":False},
  {"id":"xedapdanang","name":"XĐ Đà Nẵng – Đức Liên","region":"trung","url":"https://xedapdanang.vn/","base":"https://xedapdanang.vn","me":False},
  {"id":"xedapthegioi","name":"Xe Đạp Thế Giới","region":"nam","url":"https://xedapthegioi.vn/","base":"https://xedapthegioi.vn","me":False},
]
HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gia-lich-su.json")
UA = {"User-Agent":"Mozilla/5.0 (compatible; XDGK-PriceWatch/1.0)"}
PRICE_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|VND)", re.I)
LINK_RE  = re.compile(r"/(?:products|product|san-pham)/[^\"'#?\s]+")

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read()
        charset = res.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")

def num(s): return int(re.sub(r"[.,]","",s))

class Prod(HTMLParser):
    """Gom text + link + <del> theo từng khối sản phẩm dựa trên thẻ <a> chứa link sản phẩm."""
    def __init__(self, base):
        super().__init__(); self.base=base
        self.chunks=[]   # list of (kind, value): ('link',url) ('text',s) ('del_on',) ('del_off',) ('alt',s)
        self.in_del=0; self.skip=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ("script","style"): self.skip+=1
        if tag=="del" or (tag=="span" and "amount" in (a.get("class") or "") and self.in_del): self.in_del+= (1 if tag=="del" else 0)
        if tag=="del": pass
        if tag=="a":
            href=a.get("href") or ""
            m=LINK_RE.search(href)
            if m:
                url = href if href.startswith("http") else self.base+href
                if url.startswith(self.base):
                    self.chunks.append(("link", url.split("?")[0].rstrip("/")))
        if tag=="img":
            alt=(a.get("alt") or "").strip()
            if 3<=len(alt)<=90: self.chunks.append(("alt",alt))
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self, tag):
        if tag in ("script","style"): self.skip=max(0,self.skip-1)
        if tag=="del": self.in_del=max(0,self.in_del-1)
    def handle_data(self, d):
        if self.skip: return
        d=d.strip()
        if d: self.chunks.append(("deltext" if self.in_del else "text", d))

def parse_listing(html, src):
    p=Prod(src["base"]); p.feed(html)
    ch=p.chunks
    # vị trí các link, gộp link trùng liên tiếp
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
        # tên: alt gần nhất trong (prev_end, endi]
        slug=url.rstrip("/").split("/")[-1]
        slug_tok=set(re.split(r"[-_]+",slug.lower()))
        cands=[ch[j][1] for j in range(prev_end+1,min(next_start,len(ch))) if ch[j][0]=="alt"]
        def overlap(a):
            t=set(re.split(r"[^0-9a-zà-ỹ]+",a.lower()))
            return len(t&slug_tok)
        name=max(cands,key=overlap) if cands and max(map(overlap,cands))>=2 else None
        if not name:
            name=re.sub(r"[-_]+"," ",slug).title()
        # giá: text sau link đến trước link kế (bỏ deltext = giá gạch)
        texts=[v for k,v in ch[endi+1:next_start] if k=="text"]
        blob=" ".join(texts)[:500]
        m=re.search(r"hiện tại[^0-9]{0,20}(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|VND)", blob, re.I)
        if m: price=num(m.group(1))
        else:
            ps=[num(x) for x in PRICE_RE.findall(blob)]
            ps=[v for v in ps if 100000<=v<=200000000]
            price=min(ps) if ps else None
        if price and url not in items:
            items[url]={"name":name,"price":price,"slug":slug}; order.append(url)
    # biến thể trùng tên → thêm đuôi từ slug
    import unicodedata
    from collections import Counter
    def flat(s):
        s=s.lower().replace("\u0111","d")
        return unicodedata.normalize("NFD",s).encode("ascii","ignore").decode()
    cnt=Counter(items[u]["name"] for u in order)
    for u in order:
        it=items[u]
        if cnt[it["name"]]>1:
            fn=flat(it["name"])
            extra=" ".join(w for w in it["slug"].split("-") if flat(w) not in fn and len(w)<8)
            if extra: it["name"]+=f" ({extra})"
    return [{"url":u,**items[u]} for u in order]

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
    for s in SOURCES:
        try:
            html=fetch(s["url"]); items=parse_listing(html,s)
            if not items: raise RuntimeError("khong tim thay gia")
            for it in items:
                total+=1
                rec=hist["items"].setdefault(it["url"],{"name":it["name"],"seller":s["name"],"region":s["region"],"me":s["me"],"hist":[],"seen":t})
                rec["name"]=it["name"]; rec["seen"]=t
                h=rec["hist"]
                if not h or h[-1]["p"]!=it["price"]:
                    if h: changed+=1
                    h.append({"t":t,"p":it["price"]})
                rec["hist"]=h[-200:]
            print(f"OK  {s['name']}: {len(items)} SP")
        except Exception as e:
            print(f"ERR {s['name']}: {e}", file=sys.stderr)
    if total==0:
        print("ERR Khong cao duoc san pham nao, giu nguyen gia-lich-su.json", file=sys.stderr)
        return 1
    hist["runs"]=(hist.get("runs") or [])[-499:]+[{"t":t,"total":total,"changed":changed}]
    tmp=HIST+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(hist,f,ensure_ascii=False,separators=(",",":"))
        f.write("\n")
    os.replace(tmp,HIST)
    print(f"Tổng: {total} SP, {changed} thay đổi giá. Lưu: {HIST}")
    return 0

if __name__=="__main__": sys.exit(main())
