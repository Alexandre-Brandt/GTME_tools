"""Main category and tags per tool.

The hand-maintained source is data/tool_categories.csv (UUID, Tool Name, Main category, Tags).
Edit that file, then merge it into the working CSV:

  python3 -I scripts/categories.py check    validate data/tool_categories.csv against the lists below
  python3 -I scripts/categories.py apply    write "Main category" and "Tags" into output/combined_tools_enriched.csv

Tags are separated by "; " and start with the main category.
A value that is not in the lists below is reported by `check`; add it to the list if it is wanted.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'output/combined_tools_enriched.csv'
SOURCE = ROOT / 'data/tool_categories.csv'
SEP = '; '

MAIN_CATEGORIES = [
    'Lead generation', 'Signals & intent', 'Web scraping', 'Sales engagement',
    'Email infrastructure', 'Calling & dialers', 'Conversation intelligence', 'CRM',
    'Lead routing & scheduling', 'Forecasting & pipeline', 'CPQ & billing', 'Sales enablement',
    'Email marketing & automation', 'Advertising', 'Websites & e-commerce', 'Content & social media',
    'Customer success & support', 'Partnerships & referrals', 'Workflow automation',
    'AI assistants & LLMs', 'AI agents', 'Knowledge & company brain',
    'Communication & productivity', 'Data & analytics', 'Developer tools', 'Learning & research',
]

TAGS = MAIN_CATEGORIES + [
    # data and prospecting
    'Contact data', 'Email finder', 'Phone numbers', 'People search', 'Company data',
    'Company register data', 'Local business data', 'Data source', 'Data API',
    'Lead enrichment', 'Account enrichment', 'Waterfall enrichment', 'Data transformation',
    'Data cleaning', 'LinkedIn data', 'Relationship mapping', 'Warm intros',
    # signals
    'Intent signals', 'Website visitor identification', 'Social signals', 'Hiring signals',
    'Technographics', 'Web traffic data', 'SEO',
    # scraping
    'Data extraction', 'Web search API', 'Browser automation', 'Proxies',
    # outreach
    'Email outreach', 'LinkedIn automation', 'Multichannel outreach', 'Unified inbox',
    'SMS', 'Messaging apps', 'Direct mail', 'Gifting', 'AI SDR', 'AI writing',
    # email infrastructure
    'Mailbox setup', 'Deliverability', 'Email verification', 'Email authentication',
    'Transactional email',
    # calling and meetings
    'Cold calling', 'Power dialer', 'VoIP', 'AI voice agent', 'Call recording',
    'Meeting notes', 'Transcription', 'Meeting scheduling',
    # sales process
    'CRM updates', 'Deal intelligence', 'Pipeline management', 'Forecasting',
    'Revenue analytics', 'Business planning', 'Lead routing', 'CPQ', 'Billing',
    'Subscription analytics', 'Contracts & e-signature', 'Document generation',
    'Digital sales room', 'Mutual action plan', 'Presentations', 'Lightweight CRM', 'ERP',
    'All-in-one sales platform', 'App marketplace',
    # marketing
    'Email marketing', 'Marketing automation', 'Paid ads', 'Retargeting', 'Website builder',
    'E-commerce', 'Social media content', 'Video', 'Webinars',
    # post-sale and partners
    'Customer success', 'Customer support', 'Live chat', 'Partner management',
    'Referral programs', 'Affiliate marketing', 'Loyalty & promotions',
    # automation and AI
    'iPaaS', 'RPA', 'MCP', 'LLM', 'AI assistant', 'AI research', 'AI coding', 'Vibe coding',
    'AI image generation', 'AI video generation', 'Agent framework', 'Agent memory',
    # knowledge, communication, data, dev
    'Company brain', 'Knowledge base', 'Documentation', 'Process mapping',
    'Whiteboard & diagrams', 'Email client', 'Calendar', 'Team messaging', 'Community',
    'Voice dictation', 'Spreadsheet', 'Database', 'Data warehouse', 'Data pipelines',
    'Business intelligence', 'Code editor', 'Code hosting', 'API marketplace',
    'Maps & geodata', 'Open source',
    # learning and research
    'Online courses', 'Software reviews', 'Software pricing',
]


def load_source():
    with open(SOURCE, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def check():
    """Return a list of problems in data/tool_categories.csv (empty = all good)."""
    rows = load_source()
    problems = []
    with open(CSV, encoding='utf-8', newline='') as f:
        uuids = {r['UUID'] for r in csv.DictReader(f)}
    seen = Counter(r['UUID'] for r in rows)
    for u, n in seen.items():
        if n > 1:
            problems.append(f'UUID {u} appears {n} times')
    for u in uuids - set(seen):
        problems.append(f'UUID {u} has no category row')
    for r in rows:
        name, main = r['Tool Name'], r['Main category'].strip()
        tags = [t.strip() for t in r['Tags'].split(';') if t.strip()]
        if r['UUID'] not in uuids:
            problems.append(f'{name}: UUID not in the working CSV')
        if main not in MAIN_CATEGORIES:
            problems.append(f'{name}: unknown main category "{main}"')
        if not tags or tags[0] != main:
            problems.append(f'{name}: first tag should be the main category')
        for t in tags:
            if t not in TAGS:
                problems.append(f'{name}: unknown tag "{t}"')
        if len(tags) != len(set(tags)):
            problems.append(f'{name}: duplicate tag')
    return problems


def apply():
    problems = check()
    if problems:
        sys.exit('Not applied, fix these first:\n  ' + '\n  '.join(problems))
    by_uuid = {r['UUID']: r for r in load_source()}
    with open(CSV, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    new = [c for c in ('Main category', 'Tags') if c not in fields]
    if new:  # place the new columns right after the chat "Category" column
        i = fields.index('Category') + 1
        fields = fields[:i] + new + fields[i:]
    for r in rows:
        src = by_uuid[r['UUID']]
        r['Main category'] = src['Main category'].strip()
        r['Tags'] = SEP.join(t.strip() for t in src['Tags'].split(';') if t.strip())
    with open(CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'wrote Main category and Tags for {len(rows)} rows to {CSV.relative_to(ROOT)}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'check':
        p = check()
        print('\n'.join(p) if p else 'OK: all rows valid')
        sys.exit(1 if p else 0)
    elif cmd == 'apply':
        apply()
    else:
        sys.exit(__doc__)
