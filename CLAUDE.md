# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A data project, not an app. It builds a list of GTM / sales tools (296 rows) mentioned in two Berlin WhatsApp groups (BerlinRevOpsChapter, ClayClubBerlin), then enriches each tool with URLs, saved web pages, freemium/trial flags and categories. The original brief is `request/Request.md`; the roadmap is `todo.md`.

**Read `output/next_steps.md` before doing any data work.** It is the running log of what was done, the decisions made (and why), the open issues and the rules a later session must follow to stay consistent. Update it (and its "Last updated" line) after each step.

## Commands

Plain Python 3, standard library only. No build, lint or tests. Run scripts with `python3 -I` (isolated mode) from any directory; paths resolve from the script location.

```sh
python3 -I scripts/pricing_flags.py report out.tsv   # dry run of the freemium/trial detection
python3 -I scripts/pricing_flags.py apply            # write Has freemium / Has trial / For manual review
python3 -I scripts/categories.py check               # validate data/tool_categories.csv
python3 -I scripts/categories.py apply               # copy Main category / Tags into the working CSV
python3 -I scripts/fetch_pages.py status             # page-fetch state (full workflow in scripts/README.md)
python3 -I scripts/build_site.py                     # website data: site/data.json
python3 -m http.server -d site 8000                  # preview the website locally
```

`scripts/README.md` documents every script.

## Data flow

1. `scripts/chat_analysis/*_tools.py` read `data/transcripts/` (gitignored) and write the per-group lists `data/clayclub_tools.csv` and `data/revopschat_tools.csv`. The tool names are curated by hand inside the scripts.
2. These were merged and de-duplicated into `data/combined_tools.csv`, the clean baseline with no web results.
3. `output/combined_tools_enriched.csv` is the **working file**: same rows and UUIDs, plus the enrichment columns. The URL search (WebSearch/Tavily) and the duplicate merge were one-off session steps, not scripts. Their rules are in `next_steps.md`.
4. `scripts/fetch_pages.py` saves pages to `data/websites-markdown/` as `<UUID>.md` (homepage), `<UUID>_product.md` and `<UUID>_pricing.md`, each with a front-matter header. The `tavily_extract` call is an MCP tool, so a session makes the call and the script plans the batches and ingests the results. Run state is kept in `scripts/fetch_state/`.
5. `scripts/pricing_flags.py` reads only the saved `_pricing.md` files.
6. `scripts/categories.py` merges `data/tool_categories.csv` into the working CSV.

7. `scripts/build_site.py` publishes a subset of the working CSV as `site/data.json` (generated and gitignored). `site/` is a static page (Tabulator + Chart.js from CDNs at pinned versions, no bundler) hosted on Cloudflare Pages. The page is gated by Cloudflare Access (an email allow-list). Pushing to `main` rebuilds and redeploys it.

`UUID` (left-most column) is the join key across the CSVs and the markdown files.

## Conventions that matter

- **Generated columns are overwritten on every `apply`.** Never hand-edit `Has freemium`, `Has trial`, `For manual review`, `Main category` or `Tags` in the working CSV:
  - Categories: edit `data/tool_categories.csv`.
  - Pricing corrections: add them to `OVERRIDE` / `UNRESOLVED` in `pricing_flags.py`.
- Categories come from fixed lists (`MAIN_CATEGORIES`, `TAGS` in `categories.py`). A new tag must be added there first.
  - Tags are joined by `; ` and the first tag is the main category.
  - Don't use very broad categories such as "Revenue operations" or "Marketing".
  - Features of a parent product (HubSpot Breeze, Claygent) take the parent's main category plus an `AI agents` tag.
- Flag values are `Yes` / `No` / `Unknown`. Use `No` only when the page explicitly says so. The user filters on `Unknown` for manual review.
- Only record URLs that actually appeared in search results, never guessed ones. Sub-products use the parent's domain.
- CSV writing: UTF-8, no BOM, `csv.DictWriter(..., lineterminator='\n')`. Keep the column order.
- `data/clayclub_tools.csv`, `data/revopschat_tools.csv` and `data/stats/` are original outputs. Leave them unchanged.
- **Never publish `Mentioned by`** (names of people in the WhatsApp groups) or the transcripts on the website. `COLUMNS` in `build_site.py` is the allow-list of published columns.

## Working with the user

- The user runs git commands themselves to learn. Suggest the commands, but don't commit or push unless asked.
- macOS gotchas: the filesystem is case-insensitive (a case-only rename needs two `git mv` steps), `sed` is BSD (no `\b`, use perl), and `grep` is ugrep (complex regexes can fail, use Python).
