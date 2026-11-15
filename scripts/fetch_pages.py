#!/usr/bin/env python3
"""Fetch company/product/pricing pages with Tavily extract and save them as markdown.
Run from anywhere with: python3 -I scripts/fetch_pages.py <cmd> ...

Commands
  plan                       build stage-1 batches (company/product pages) -> plan_company.json
  pricing_plan               build stage-2 batches (pricing pages) from the saved company pages -> plan_pricing.json
  urls <stage> <b>           print the JSON list of unique URLs of batch b (stage = company|pricing)
  ingest <stage> <b> <file>  read a saved tavily_extract result file, write markdown files, record status
  merge                      write recorded status into output/combined_tools_enriched.csv (run once, at the end)
  status                     print progress

Environment: FETCH_DEPTH (basic|advanced, only recorded in the file header), FETCH_DATE (default today).
The tavily_extract call itself is made by an agent/session; this script only plans batches, ingests
the saved result file and merges status into the CSV. See scripts/README.md.
"""
import csv, json, re, sys, os, glob
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
ROOT = str(HERE.parent)
CSV = f'{ROOT}/output/combined_tools_enriched.csv'
MD = f'{ROOT}/data/websites-markdown'
ST = str(HERE / 'fetch_state')   # plans and per-batch status files
DATE = os.environ.get('FETCH_DATE', date.today().isoformat())
BATCH = 20
MIN_CHARS = 500
MAX_CHARS = 200000
DEPTH = os.environ.get('FETCH_DEPTH', 'basic')
os.makedirs(ST, exist_ok=True)


def norm(u):
    u = u.strip().lower()
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'^www\.', '', u)
    return u.rstrip('/')


def load_rows():
    return list(csv.DictReader(open(CSV, encoding='utf-8', newline='')))


def batches(units):
    """group units by unique normalised url, BATCH urls per batch"""
    seen, order = {}, []
    for i, u in enumerate(units):
        k = norm(u['url'])
        if k not in seen:
            seen[k] = []
            order.append(k)
        seen[k].append(i)
    out = []
    for s in range(0, len(order), BATCH):
        out.append([i for k in order[s:s + BATCH] for i in seen[k]])
    return out


def save_plan(name, units):
    b = batches(units)
    json.dump({'units': units, 'batches': b}, open(f'{ST}/plan_{name}.json', 'w'), indent=0)
    nurl = sum(len({norm(units[i]['url']) for i in bb}) for bb in b)
    print(f'{name}: {len(units)} units, {nurl} unique urls, {len(b)} batches of <= {BATCH} urls')


def cmd_plan():
    units = []
    for r in load_rows():
        if not r['Company URL'] or r['Fetch check']:
            continue
        units.append({'uuid': r['UUID'], 'tool': r['Tool Name'], 'kind': 'company', 'url': r['Company URL']})
        if r['Product URL'] and norm(r['Product URL']) != norm(r['Company URL']):
            units.append({'uuid': r['UUID'], 'tool': r['Tool Name'], 'kind': 'product', 'url': r['Product URL']})
    save_plan('company', units)


def same_site(host, base):
    h = host.lower().removeprefix('www.')
    b = base.lower().removeprefix('www.')
    return h == b or h.endswith('.' + b) or b.endswith('.' + h)


def read_md(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n\n', t, re.S)
    meta = dict(l.split(': ', 1) for l in m.group(1).split('\n') if ': ' in l) if m else {}
    return meta, t[m.end():] if m else t


def cmd_pricing_plan():
    units = []
    for r in load_rows():
        uid = r['UUID']
        cpath = f'{MD}/{uid}.md'
        ppath = f'{MD}/{uid}_pricing.md'
        if not os.path.exists(cpath) or os.path.exists(ppath):
            continue
        if r['Pricing URL']:
            units.append({'uuid': uid, 'tool': r['Tool Name'], 'kind': 'pricing', 'url': r['Pricing URL'], 'how': 'known'})
            continue
        meta, body = read_md(cpath)
        src = meta.get('source_url') or r['Company URL']
        base = urlparse(r['Company URL']).netloc or urlparse(src).netloc
        cands = []
        for text, href in re.findall(r'\[([^\]]*)\]\(([^)\s]+)', body):
            if href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
                continue
            full = urljoin(src, href).split('#')[0]
            p = urlparse(full)
            if p.scheme not in ('http', 'https') or not same_site(p.netloc, base):
                continue
            if re.search(r'pric|plans', p.path, re.I) or re.fullmatch(r'\s*(pricing|plans( & pricing)?|prices)\s*', text, re.I):
                cands.append(full)
        if cands:
            cands.sort(key=lambda c: (0 if 'pricing' in c.lower() else 1, len(c)))
            units.append({'uuid': uid, 'tool': r['Tool Name'], 'kind': 'pricing', 'url': cands[0], 'how': 'link'})
        else:
            o = urlparse(r['Company URL'])
            units.append({'uuid': uid, 'tool': r['Tool Name'], 'kind': 'pricing', 'url': f'{o.scheme}://{o.netloc}/pricing', 'how': 'guess'})
    save_plan('pricing', units)


def get_plan(stage):
    return json.load(open(f'{ST}/plan_{stage}.json'))


def cmd_urls(stage, b):
    p = get_plan(stage)
    seen, out = set(), []
    for i in p['batches'][int(b)]:
        u = p['units'][i]['url']
        if norm(u) not in seen:
            seen.add(norm(u))
            out.append(u)
    print(json.dumps(out))


def state_path(stage, b):
    return f'{ST}/state_{stage}_{int(b):02d}.json'


def cmd_ingest(stage, b, resfile):
    p = get_plan(stage)
    raw = open(resfile, encoding='utf-8').read()
    try:
        d = json.loads(raw)
    except Exception as e:
        print('ERROR: result file is not valid JSON:', e)
        sys.exit(1)
    ok = {norm(r['url']): r for r in d.get('results', [])}
    bad = {norm(r['url']): r.get('error', '?') for r in d.get('failed_results', [])}
    res, n_ok, fails = [], 0, []
    for i in p['batches'][int(b)]:
        u = p['units'][i]
        k = norm(u['url'])
        r = ok.get(k)
        if r is None:   # tolerate redirects such as trailing path changes
            r = next((x for kk, x in ok.items() if kk.split('/')[0] == k.split('/')[0] and kk.startswith(k)), None)
        rec = dict(u)
        c = (r or {}).get('raw_content') or ''
        if r is not None and len(c) >= MIN_CHARS:
            suffix = '' if u['kind'] == 'company' else f"_{u['kind']}"
            orig = len(c)
            trunc = ''
            if orig > MAX_CHARS:
                c = c[:MAX_CHARS]
                trunc = f"truncated: true (original {orig} chars)\n"
            hdr = (f"---\nuuid: {u['uuid']}\ntool: {u['tool']}\nsource_url: {r['url']}\n"
                   f"title: {(r.get('title') or '').replace(chr(10), ' ')}\nfetched: {DATE}\n"
                   f"fetched_with: tavily_extract ({DEPTH})\n{trunc}---\n\n")
            open(f"{MD}/{u['uuid']}{suffix}.md", 'w', encoding='utf-8').write(hdr + c)
            rec.update(status='fetched', chars=len(c), date=DATE)
            n_ok += 1
        else:
            why = bad.get(k) or ('empty/short content' if r is not None else 'no result returned')
            rec.update(status='failed', error=why[:120], date=DATE)
            fails.append(f"{u['tool']} [{u['kind']}] {u['url']}: {why[:60]}")
        res.append(rec)
    json.dump(res, open(state_path(stage, b), 'w'), indent=0)
    print(f'{stage} batch {b}: {n_ok} fetched, {len(fails)} failed of {len(res)} units')
    for f in fails:
        print('  FAIL', f)


def cmd_merge():
    rows = load_rows()
    by = {r['UUID']: r for r in rows}
    comp, pric = {}, {}
    for f in sorted(glob.glob(f'{ST}/state_company_*.json')) + sorted(glob.glob(f'{ST}/state_retry_*.json')):
        for rec in json.load(open(f)):
            if rec['kind'] == 'company':
                comp[rec['uuid']] = rec
    for f in sorted(glob.glob(f'{ST}/state_pricing_*.json')):
        for rec in json.load(open(f)):
            pric[rec['uuid']] = rec
    n = [0, 0, 0]
    for uid, rec in comp.items():
        r = by[uid]
        r['Fetch check'] = 'fetched' if rec['status'] == 'fetched' else 'fetch failed'
        r['Fetch check date'] = rec.get('date') or DATE
        n[0 if rec['status'] == 'fetched' else 1] += 1
    for uid, rec in pric.items():
        if rec['status'] == 'fetched':
            by[uid]['Pricing URL'] = rec['url']
            n[2] += 1
    with open(CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'merged: {n[0]} fetched, {n[1]} fetch failed, {n[2]} pricing pages fetched')


def cmd_status():
    for stage in ('company', 'pricing'):
        pf = f'{ST}/plan_{stage}.json'
        if not os.path.exists(pf):
            print(stage, 'no plan yet')
            continue
        p = json.load(open(pf))
        done = sorted(glob.glob(f'{ST}/state_{stage}_*.json'))
        print(f'{stage}: {len(done)}/{len(p["batches"])} batches ingested')


if __name__ == '__main__':
    c, a = sys.argv[1], sys.argv[2:]
    {'plan': cmd_plan, 'pricing_plan': cmd_pricing_plan, 'urls': cmd_urls, 'ingest': cmd_ingest,
     'merge': cmd_merge, 'status': cmd_status}[c](*a)
