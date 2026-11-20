"""Build the data file for the static website in site/.

  python3 -I scripts/build_site.py

Reads output/combined_tools_enriched.csv and writes site/data.json with only the
columns the site shows. "Mentioned by" (names of people from the WhatsApp groups)
and the internal pipeline columns are left out on purpose: they must not go online.

Cloudflare Pages runs this as the build command on every push (output folder: site).
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'output/combined_tools_enriched.csv'
OUT = ROOT / 'site/data.json'

# CSV column -> JSON key. Anything not listed here is not published.
COLUMNS = {
    'UUID': 'id',
    'Tool Name': 'name',
    'Main category': 'main',
    'Tags': 'tags',
    'Category': 'chat_category',
    'Company URL': 'company_url',
    'Product URL': 'product_url',
    'Pricing URL': 'pricing_url',
    'Has freemium': 'freemium',
    'Has trial': 'trial',
    'For manual review': 'review',
}
FLAG_VALUES = {'Yes', 'No', 'Unknown'}


def main():
    with open(CSV, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in reader.fieldnames]
        if missing:
            sys.exit(f'{CSV.relative_to(ROOT)} is missing columns: {", ".join(missing)}')
        rows = list(reader)

    tools, problems = [], []
    for r in rows:
        t = {key: r[col].strip() for col, key in COLUMNS.items()}
        t['tags'] = [s.strip() for s in t['tags'].split(';') if s.strip()]
        for flag in ('freemium', 'trial'):
            if t[flag] not in FLAG_VALUES:
                problems.append(f'{t["name"]}: {flag} = "{t[flag]}"')
        if not t['main']:
            problems.append(f'{t["name"]}: no main category')
        tools.append(t)
    if problems:
        sys.exit('Not built, fix these first:\n  ' + '\n  '.join(problems))

    tools.sort(key=lambda t: t['name'].casefold())
    data = {
        'built_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'count': len(tools),
        'tools': tools,
    }
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'wrote {len(tools)} tools to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
