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

## pricing_flags.py (freemium and trial, step 4)

Fills `Has freemium`, `Has trial` (`Yes` / `No` / `Unknown`) and `For manual review` in `output/combined_tools_enriched.csv` from the saved pricing pages.

```
python3 -I scripts/pricing_flags.py report out.tsv   # dry run: one row per tool with the matched phrase
python3 -I scripts/pricing_flags.py apply            # write the three columns to the CSV
```

- Safe to rerun: `apply` recomputes the three columns from the pages every time, so **manual edits to those columns are overwritten**. Put lasting corrections in `OVERRIDE` (or `UNRESOLVED`) inside the script.
- The matching rules and why they are the way they are: `output/next_steps.md`, step 4.

## categories.py (main category and tags)

Copies `Main category` and `Tags` from `data/tool_categories.csv` (the hand-edited source) into `output/combined_tools_enriched.csv`.

```
python3 -I scripts/categories.py check   # unknown categories/tags, missing or duplicate UUIDs
python3 -I scripts/categories.py apply   # runs check first, then writes the two columns
```

- The allowed main categories and tags are the two lists at the top of the script. Add a tag there before using it.
- Tags are separated by `; ` and the first tag is always the main category.

## build_site.py (website)

Writes `site/data.json` from `output/combined_tools_enriched.csv`. The website itself is `site/index.html`, `site/app.js` and `site/style.css`: plain files with no build step. Tabulator 6.3.1 (table) and Chart.js 4.4.7 (charts) are loaded from CDNs at pinned versions.

```
python3 -I scripts/build_site.py              # writes site/data.json
python3 -m http.server -d site 8000           # preview at http://localhost:8000
```

- Only the columns listed in `COLUMNS` are published. **`Mentioned by` (people's names) and the internal pipeline columns are left out on purpose.** Don't add them.
- `site/data.json` is generated and gitignored. Cloudflare builds it on every deploy.
- Filters are kept in the URL hash, so a filtered view can be bookmarked or shared, e.g. `#main=CRM&freemium=Yes`.

### Hosting: Cloudflare Workers (static assets) + Cloudflare Access (free)

`wrangler.jsonc` (at the project root) tells Cloudflare to serve the `site/` folder. There is no server code. Cloudflare now sends new static sites to Workers instead of Pages, which is why this is a Worker.

Set up once:

1. Go to **Compute → Workers & Pages → Create application → Import a repository** and pick `GTME_tools`. Settings:
   - Project name: `gtme-tools` (must match `name` in `wrangler.jsonc`)
   - Build command: `python3 scripts/build_site.py`
   - Deploy command: `npx wrangler deploy`

   Every push to `main` then rebuilds and redeploys the site at `https://gtme-tools.<subdomain>.workers.dev`.
2. In Zero Trust, choose the **Free** plan (up to 50 users; it may ask for a card even at $0). The team name is `alex-gtm-tools`.
3. Gate the site: open the Worker → **Access** tab → **Protect this Worker behind Access**.
   - Scope: **All traffic**. The default, "Previews only", leaves the live site public.
   - Authentication policy: one of the two preconfigured policies, either of which lets in only the owner today:
     - **Email domain** (`bingo-films.com`, with a one-time code sent by email)
     - **Cloudflare account** (members of this Cloudflare account only)
   - Click **Apply Access**.
4. Check the gate. In a private browser window:
   - `https://gtme-tools.alexandre-3d6.workers.dev` and `/data.json` should both show the Cloudflare login page.
   - After you log in, the site loads.

To give someone outside the domain access, go to Zero Trust → **Access → Policies** and create an Allow policy that includes **Emails**. Attach it to the `gtme-tools` application, and make sure **One-time PIN** is enabled as a login method. No redeploy is needed. Per-branch preview URLs are switched off in `wrangler.jsonc`, so only `main` is ever online.

## Not saved on purpose

- The WebSearch/Tavily URL enrichment, the Tavily clean-ups and the 10-pair duplicate merge were done as one-off steps in the session and are not scripts. What was decided and why is in `output/next_steps.md`.
- `tools.py` (an early RevOps list superseded by `revops_tools.py`) and the old pilot helpers `apply.py` and `merge.py` (they point at files that no longer exist).
