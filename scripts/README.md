# scripts

Everything here is plain Python 3 with no extra packages. Paths are relative to the project root, so run from anywhere, e.g. `python3 -I scripts/fetch_pages.py status`.

## chat_analysis/ (first sessions)

Rebuild the per-group tool lists from the WhatsApp exports in `data/transcripts/`.

| Script | What it does |
|---|---|
| `clay_tools.py` | Reads the ClayClubBerlin export, applies the hand-curated tool list and mention matching, writes `data/clayclub_tools.csv` and prints the 3-KPI stats. |
| `revops_tools.py` | Same for BerlinRevOpsChapter, writes `data/revopschat_tools.csv`. |
| `parse.py <file>`, `parse2.py <file> <group...>` | Small exploration helpers for reading messages and counting authors. |

Both tool-list scripts were re-run on 2026-11-13 and reproduce the CSVs byte for byte. The tool names and categories are curated by hand inside the scripts (they are not auto-detected), so edit the lists there if you change a name.

## fetch_pages.py (page fetch, step 3)

Saves company, product and pricing pages as markdown in `data/websites-markdown/` and records the result in `output/combined_tools_enriched.csv`.

The `tavily_extract` call itself is not in the script (it is an MCP tool). A session or subagent makes the call, and the script handles everything around it:

```
python3 -I scripts/fetch_pages.py plan                        # company + product pages -> scripts/fetch_state/plan_company.json
python3 -I scripts/fetch_pages.py urls company 0              # URLs of batch 0 (<= 20)
#   -> call tavily_extract(urls, format=markdown, extract_depth=basic); a large result is saved by Claude Code to a file
python3 -I scripts/fetch_pages.py ingest company 0 <result file>   # writes <UUID>.md / _product.md, records status
python3 -I scripts/fetch_pages.py pricing_plan                # after the company pages: pricing links, else <domain>/pricing
python3 -I scripts/fetch_pages.py urls pricing 0
python3 -I scripts/fetch_pages.py ingest pricing 0 <result file>
python3 -I scripts/fetch_pages.py merge                       # Fetch check, Fetch check date, Pricing URL -> CSV
python3 -I scripts/fetch_pages.py status
```

- `plan` skips rows whose `Fetch check` is already filled, so a rerun only picks up new or unfetched rows.
- Pages over 200,000 characters are cut, and the header says `truncated: true`.
- Failed pages are recorded with the reason in `scripts/fetch_state/state_*.json`. `merge` is safe to repeat (it uses the date stored in each record).
- Set `FETCH_DEPTH=advanced` when ingesting advanced-depth results so the file header is right.
- `scripts/fetch_state/` holds the plans and results of the 2026-11-13 run (642 records). `state_retry_00.json` is the advanced-depth retry; it overrides the earlier failures in `merge`.
- Pricing pages with almost no pricing words were deleted by hand after the run (15 of them) and marked failed in the state files. The script does not do that check yet.

## Not saved on purpose

- The WebSearch/Tavily URL enrichment, the Tavily clean-ups and the 10-pair duplicate merge were done as one-off steps in the session and are not scripts. What was decided and why is in `output/next_steps.md`.
- `tools.py` (an early RevOps list superseded by `revops_tools.py`) and the old pilot helpers `apply.py` and `merge.py` (they point at files that no longer exist).
