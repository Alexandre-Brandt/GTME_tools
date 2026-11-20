"""Step 4: fill Has freemium / Has trial from the saved pricing pages.

Reads data/websites-markdown/<UUID>_pricing.md and matches wording, not prices
(extracted prices are sometimes garbled).

  python3 -I scripts/pricing_flags.py report [out.tsv]   dry run: summary + one row per tool with the matched text
  python3 -I scripts/pricing_flags.py apply              write Has freemium, Has trial, For manual review to the CSV

Values: Yes when the page says so, No only when the page says there is none,
Unknown when the page does not say (or there is no pricing page). Rows where the page only says something vague
("start for free", "try for free") get a note in "For manual review".
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'output/combined_tools_enriched.csv'
MD = ROOT / 'data/websites-markdown'
REVIEW_COL = 'For manual review'

# Rows that could not be resolved in the URL search (output/next_steps.md, step 1).
UNRESOLVED = {
    'Calltime': 'URL: only calltime.ai found (political fundraising software), probably the wrong tool',
    'Cost': 'URL: chat link is lcobuilder.com ("LCO - AI VP of Sales"), name "Cost" may be a transcription slip',
    'Growblocks': 'URL: growblocks.com is a domain-for-sale page, company may be gone',
    'Sectorlens': 'URL: sectorlens.de (Berlin AI agency) not confirmed as the job-ads data tool',
}

F = re.IGNORECASE
FREEMIUM_YES = [
    r'free plan', r'free forever', r'forever free', r'free tier',
    r'free version', r'free edition', r'community edition', r'free account',
    r'free for (?:up to|individuals?|personal|small teams|startups|everyone|\d+(?!\d)(?!\s*(?:days?|weeks?|months?|years?)))',
    # $0 only with a billing period after it, or right after the word "Free"
    # (a bare $0 also shows up in sliders, add-ons and usage tables)
    r'(?<!from )(?<![\w.])[$€£]\s?0(?:\.00)?(?![\d.,])\s*(?:/\s*(?:mo|month|mth|user|seat)|per\s+(?:user|seat|month)|monthly|forever|USD per)',
    r'\bfree\W{0,8}[$€£]\s?0(?![\d.,])(?!\s*(?:to start|for \d))',
    r'(?m)^\s*#{1,6}\s*\**\s*free\s*\**\s*$',          # a plan heading called "Free"
    r'kostenlose[rn]? (?:plan|version|tarif|paket)', r'f(?:ü|ue)r immer kostenlos',
]
NOT = r"(?:don[’']?t|do not|doesn[’']?t|does not|won[’']?t)"
FREEMIUM_NO = [
    r'no free (?:plan|tier|version)',
    NOT + r' (?:offer|have|provide) (?:a |any )?free (?:plan|tier|version)',
]
TRIAL_YES = [
    r'free trial', r'\d+[- ]days? (?:free )?trial', r'trial (?:of|for) \d+ days',
    r'trial period', r'start (?:your |a )?trial', r'free for \d+ days?',
    r'kostenlos testen', r'testphase', r'testversion', r'\d+ tage (?:kostenlos|gratis|testen)',
]
TRIAL_NO = [
    r'no free trial', NOT + r' (?:offer|have|provide) (?:a |any )?(?:free )?trials?',
    r'free trial (?:is )?not available', r'instead of (?:a )?free trials?',
]

# Matches checked by hand and found wrong: ignore the "yes" for that field.
OVERRIDE = {
    'Teamfluence': ('freemium', 'Freemium: "free forever" on the pricing page is a quoted example, not their plan'),
}
VAGUE = [  # free, but could be a free plan or a trial
    r'(?:start|get started|begin|sign up|try(?: it)?)(?: for)? free(?!\s*trial)',
]


def find(patterns, text, questions=None):
    """Return the matched phrase for each pattern that matches.

    Matches inside a question ("Is there a free plan?") are skipped and, if a
    list is given, collected in `questions` instead.
    """
    hits = []
    for p in patterns:
        for m in re.finditer(p, text, F):
            line_end = text.find('\n', m.end())
            rest = text[m.end():line_end if line_end != -1 else len(text)]
            q = re.match(r'[^.!\n]{0,40}\?', rest)
            if q:
                # FAQ: look at the first word of the answer
                after = text[m.end() + q.end():m.end() + q.end() + 40]
                before = text[max(0, m.start() - 50):m.start()]
                asks_exists = re.search(
                    r'(?:is there|are there|do you (?:offer|have|provide)|does \S+(?: \S+)? (?:offer|have|provide)'
                    r'|can i (?:get|try|use)|is \S+ free|offer)\W+(?:a |an |any )?(?:\S+ )?$', before, F)
                answer = asks_exists and re.match(r'[\s*#_]*(yes|no)\b', after, F)
                phrase = re.sub(r'\s+', ' ', m.group()).strip()
                if answer and answer.group(1).lower() == 'yes':
                    hits.append(phrase + '? Yes')
                    break
                if questions is not None:
                    questions.append((phrase, answer.group(1).lower() if answer else None))
                continue
            hits.append(re.sub(r'\s+', ' ', m.group()).strip())
            break
    return hits


def strip(patterns, text):
    """Blank out negated phrases so "no free trial" does not also count as "free trial"."""
    for p in patterns:
        text = re.sub(p, lambda m: ' ' * len(m.group()), text, flags=F)
    return text


def body(path):
    text = path.read_text(encoding='utf-8')
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            text = text[end + 4:]
    return text


def decide(yes, no):
    if yes and no:
        return 'Unknown', True   # contradictory: flag
    if yes:
        return 'Yes', False
    if no:
        return 'No', False
    return 'Unknown', False


def classify(row):
    """-> (has_freemium, has_trial, review_notes, evidence)"""
    notes = []
    if row['Tool Name'] in UNRESOLVED:
        notes.append(UNRESOLVED[row['Tool Name']])
    path = MD / f"{row['UUID']}_pricing.md"
    if not path.exists():
        return 'Unknown', 'Unknown', notes, 'no pricing page'
    text = body(path)
    fn, tn = find(FREEMIUM_NO, text), find(TRIAL_NO, text)
    rest = strip(FREEMIUM_NO + TRIAL_NO, text)
    asked_f, asked_t = [], []
    fy, ty = find(FREEMIUM_YES, rest, asked_f), find(TRIAL_YES, rest, asked_t)
    # an FAQ question answered "No" counts as a no
    fn += [f'{p}? No' for p, a in asked_f if a == 'no']
    tn += [f'{p}? No' for p, a in asked_t if a == 'no']
    asked_f = [p for p, a in asked_f if a is None]
    asked_t = [p for p, a in asked_t if a is None]
    asked = asked_f + asked_t
    if row['Tool Name'] in OVERRIDE:
        field, note = OVERRIDE[row['Tool Name']]
        if field == 'freemium':
            fy = []
        else:
            ty = []
        notes.append(note)
    freemium, f_conflict = decide(fy, fn)
    trial, t_conflict = decide(ty, tn)
    if f_conflict:
        notes.append('Freemium: pricing page says both yes and no')
    if t_conflict:
        notes.append('Trial: pricing page says both yes and no')
    if not (fy or fn or ty or tn):
        vague = find(VAGUE, rest)
        if asked:
            notes.append(f'Freemium/trial: pricing page only asks "{asked[0]}?" (check the FAQ answer)')
        elif vague:
            notes.append(f'Freemium/trial: pricing page only says "{vague[0]}"')
    else:
        if asked_f and not (fy or fn):
            notes.append(f'Freemium: pricing page only asks "{asked_f[0]}?" (check the FAQ answer)')
        if asked_t and not (ty or tn):
            notes.append(f'Trial: pricing page only asks "{asked_t[0]}?" (check the FAQ answer)')
    evidence = ' || '.join(
        f'{k}: {v[0]}' for k, v in
        (('free+', fy), ('free-', fn), ('trial+', ty), ('trial-', tn)) if v)
    return freemium, trial, notes, evidence


def load():
    with open(CSV, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def report(out):
    _, rows = load()
    counts = {}
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['Tool Name', 'Has freemium', 'Has trial', REVIEW_COL, 'evidence'])
        for r in rows:
            fr, tr, notes, ev = classify(r)
            w.writerow([r['Tool Name'], fr, tr, '; '.join(notes), ev])
            for k, v in (('freemium', fr), ('trial', tr)):
                counts[(k, v)] = counts.get((k, v), 0) + 1
            counts[('review', bool(notes))] = counts.get(('review', bool(notes)), 0) + 1
    for k in sorted(counts, key=str):
        print(k, counts[k])
    print('report:', out)


def apply():
    fields, rows = load()
    if REVIEW_COL not in fields:
        fields = fields + [REVIEW_COL]
    for r in rows:
        fr, tr, notes, _ = classify(r)
        r['Has freemium'], r['Has trial'] = fr, tr
        r[REVIEW_COL] = '; '.join(notes)
    with open(CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows)} rows to {CSV.relative_to(ROOT)}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'report'
    if cmd == 'report':
        report(sys.argv[2] if len(sys.argv) > 2 else 'pricing_flags_report.tsv')
    elif cmd == 'apply':
        apply()
    else:
        sys.exit(__doc__)
