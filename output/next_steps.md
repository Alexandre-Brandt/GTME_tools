# Tool enrichment: status and next steps

Last updated: 2026-11-13 (after Tavily pass, clean-ups and the page fetch)

## Where things stand

| File | What it is |
|---|---|
| `Output/combined_tools_enriched.csv` | **Working file.** 296 tools merged from the two WhatsApp groups, plus URLs found by search. All rows searched once with WebSearch; the 83 unconfirmed rows and 23 chat-only rows were then re-checked with Tavily (2026-11-13). |
| `Output/next_steps.md` | This file. |
| `Data/combined_tools.csv` | Clean baseline: same 296 rows and UUIDs, but no web results. |
| `Data/clayclub_tools.csv`, `Data/revopschat_tools.csv` | Original per-group tool lists. Untouched. |
| `Data/stats/` | The per-group 3-KPI files (`clayclub_stats.md`, `revopschat_stats.md`). |
| `Data/transcripts/` | The two WhatsApp exports (source data). |
| `scripts/` | Python scripts for the chat analysis and the page fetch, plus the fetch run state. See `scripts/README.md`. |
| `Data/websites-markdown/` | 542 fetched pages (about 7 MB): `<UUID>.md` = company homepage (288), `<UUID>_product.md` = product page (53), `<UUID>_pricing.md` = pricing page (201). Each file starts with a front-matter block (uuid, tool, source_url, title, fetched date). |

Both combined files share the same `UUID` per tool (left-most column). Use it as the join key for fetched markdown.

### Columns in `combined_tools_enriched.csv`

`UUID`, `Tool Name`, `Category`, `URL (chat)`, `Company URL`, `Product URL`, `Pricing URL`, `URL source`, `Web check`, `Fetch check`, `Fetch check date`, `Has freemium`, `Has trial`, `Mentioned by`

- `URL (chat)`: untouched, exactly what people posted.
- `Company URL`: root domain (`https://domain`, no `www.`).
- `Product URL`: only a dedicated product page. **Blank means no distinct product page** (the homepage is the product), not "not searched".
- `Pricing URL`: vendor's own pricing page, if one showed up.
- `URL source`: `Chat`, `Claude WebSearch`, `Tavily`, joined by `; ` when several sources agree.
- `Fetch check`: `fetched` (page saved) or `fetch failed`; blank where there is no Company URL. `verified` is reserved for pages a human has read. `Fetch check date`: ISO date of the fetch. `Has freemium`, `Has trial`: **still empty**, to be filled in step 4 (TRUE/FALSE only when confirmed, blank when unknown).

### `Web check` values

| Value | Meaning | Rows |
|---|---|---|
| `found` | A link on the vendor's own domain appeared in the results and matches the tool. | 278 |
| `found (retry)` | Same, but only after a second, reworded search. | 14 |
| `needs review` | Candidate or partial match that could not be confirmed. | 3 (Calltime, Cost, Sectorlens) |
| `not found` | Nothing plausible after a retry. Only `Growblocks` (domain is now for sale). | 1 |

Totals: 294 rows have a Company URL, 59 a Product URL, 8 a Pricing URL.

## Next steps (in order)

### 1. Tavily pass on the unconfirmed rows: DONE (2026-11-13)
- Ran about 123 `tavily_search` calls. 83 unconfirmed rows plus 23 chat-only `found` rows were re-checked; 82 moved to `found`, the rest only gained `Tavily` in `URL source`.
- Method that worked best: `tavily_search` with `include_domains` set to the candidate domain. A hit from that domain with matching content confirms it, and the output is short. Where there was no candidate, a plain search with the tool name and category.
- Still open (4 rows):
  - `Calltime`: only `calltime.ai` turned up, which is political fundraising software. Probably the wrong tool. Ask in the chat or drop.
  - `Cost`: chat URL is `lcobuilder.com` (site: "LCO - AI VP of Sales"). The tool is called "Cost" in the chat, so likely a transcription slip. Company URL is set but the row stays `needs review`.
  - `Growblocks`: `growblocks.com` is now a domain-for-sale page; the company may be gone. Marked `not found`.
  - `Sectorlens`: `sectorlens.de` exists (Berlin AI development agency) but I could not confirm it is the "tech / backend data from job ads" tool.
- Marked `found` but worth a human glance (the site differs from the chat description): `Freckle` (now "GTM workflows from your terminal"), `Needle` (autonomous revenue agents), `XLR8` (site branded UpPost.ai), `Oxygen` (`oxygen-agent.com`, found via a vendor-written guide), `Clay API (unofficial)` (`claygenius.io`, a Clay consultancy), `Cacheflow` (acquired by HubSpot in Oct 2024, site may redirect), `AgentGPT` (Reworkd has since pivoted), `Re2.ai` (brand is Resquared).
- Changed by Tavily: `Teamfluence` now `teamfluence.com` (was `myteamfluence.com`), `Cacheflow` now `getcacheflow.com`, `Claude / Anthropic` now `anthropic.com` plus Product `claude.com`, `Facebook Ads` now `facebook.com` plus Product `facebook.com/business/tools/ads-manager`.
- Not re-checked: the 14 `found (retry)` rows (weaker evidence) and the 173 `found` rows that WebSearch confirmed.

### 2. Small clean-ups: DONE (2026-11-13)
- `SAP Integration Suite` Product URL is now the English international page `www.sap.com/products/technology-platform/integration-suite.html`, seen in a Tavily result.
- Closely (`closelyhq.com`), Demodesk (`demodesk.com`), MillionVerifier (`millionverifier.com`), ChatGPT / OpenAI (`openai.com`) were all confirmed with Tavily.
- `Salesforce` and `Salesforce (SFDC)` confirmed on `salesforce.com`, Product URL `www.salesforce.com/crm`.
- **10 near-duplicate pairs merged** in both `Output/combined_tools_enriched.csv` and `Data/combined_tools.csv` (306 -> 296 rows, UUIDs still identical in both files). Kept the first name, combined Category and Mentioned by, dropped the second UUID:
  Apollo.io (+ Apollo), Claude / Anthropic (+ Claude (Anthropic)), Claude Code (+ the "CloudCode" row), Claygent (+ Claygent (Clay Agent)), Google Gemini (+ "incl. Gemini Canvas"), ChatGPT / OpenAI (+ the GPT-4o variant row), Intercom (+ "incl. Fin"), WhatsApp (+ "incl. WhatsApp Business API"), Zero (+ zero.inc), Microsoft Dynamics (+ Microsoft Dynamics CRM).
  Sub-products stay separate (Salesforce CPQ, HubSpot Breeze, Zapier Central and so on).
- The per-group files (`Data/clayclub_tools.csv`, `Data/revopschat_tools.csv`) and `Data/stats/` were **not** changed, so they still use the original names and counts.
- The 4 unresolved rows (Calltime, Cost, Growblocks, Sectorlens) were kept and flagged on purpose; you can check the chat context yourself later.

### 3. Fetch step: DONE (2026-11-13)
- Tool: `tavily_extract` (markdown, `basic` depth; `advanced` for the retry), 20 URLs per call, run by subagents. WebFetch was not used (it returns a model summary, not the page, and got a 403 on sap.com).
- Company homepages: 288 of 294 fetched. Product pages: 53 saved.
- Pricing pages: 201 saved. 93 came from a pricing link found on the company page, the rest from trying `<domain>/pricing`. Fetched guesses were kept only if the page had real pricing content (15 low-signal pages such as Telegram's were dropped).
- Pricing pages that failed (about 70, mostly 404 or blocked) have a blank `Pricing URL`; for these `Has freemium` / `Has trial` stay blank unless found another way.
- Size cap: pages over 200,000 characters are cut (Attention's homepage was 4.2M characters); the file header says `truncated: true`.
- Credits: roughly 480 URLs requested, about 100 credits at 1 credit per 5 pages (basic), a few more for the 14 advanced retries. Failed fetches should not be charged.
- **6 company pages still `fetch failed`:** `g2.com`, `openregister.de`, `phantombuster.com`, `sweep.io` (blocked even at advanced depth), `deepseek.com` (empty page, JavaScript app) and `tome.app` (404, the product looks dead). Options: try WebFetch or a browser, or leave blank.
- **Dead product URLs** (recorded by the earlier search, now 404 or empty): Attention (`/ads/conversation-intelligence-software/`), Default (`/product/routing`), Lucidchart (`/pages/landing/process-mapping`), Valuecase (`/digital-sales-room`), AgentGPT (`agentgpt.reworkd.ai` is an empty app shell). These Product URL cells should be corrected or blanked.
- Not done: a human read of the pages (`verified`). A sample check of 10-20 pages would be worthwhile, because some sites changed (Freckle, Needle, XLR8, Tome).
- The fetch script is saved in the project as `scripts/fetch_pages.py` (plan, ingest, merge), with the run state in `scripts/fetch_state/`. See `scripts/README.md`.

### 4. Freemium and trial
- Read the saved pricing markdown (`Data/websites-markdown/<UUID>_pricing.md`), not search snippets (snippets disagreed on prices in testing).
- Match on words (free plan, free forever, free trial, "start free", "14-day", no credit card) rather than dollar amounts: extracted prices are sometimes garbled (for example `$4435`).
- Fill `Has freemium` and `Has trial` as TRUE/FALSE, blank if the page does not say.

### 5. Optional
- Rows with no Product URL are mostly "homepage is the product". Take real product pages from the homepage fetch (step 3) rather than searching.
- Optionally re-check the 14 `found (retry)` rows with Tavily (about 14 searches).
- Replace regional product URLs where they remain (the ones fixed so far: Confluence, Salesforce AppExchange, Salesforce Revenue Cloud, SAP).

## Rules used (so a later session stays consistent)

- Search query for unsearched rows: `"<Tool>" <first category> official website` (drop notes in brackets). For rows with a chat URL: `"<Tool>" <chat domain> <first category> product features`.
- Retry once with a reworded query when no plausible vendor site appears.
- Only record URLs that actually appeared in the results, never guessed.
- Sub-products use the parent company's domain (Claude Code -> anthropic.com, Eloqua -> oracle.com).
- Weflow's correct domain is `getweflow.com` (confirmed by you), not `weflow.ai`.

## Practical notes

- `WebSearch` has a per-session cap. `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION=500` is now set in `~/.claude/settings.json` (it refills about 100 calls per hour). The default is 200.
- Subagents share that cap, and several stopped partway when it ran out. Their unfinished rows were left unsearched, not recorded as failures.
- Tavily search results are small when `include_domains` is used, so a batch of 12-14 parallel calls fits comfortably in one turn.
- Scripts are in `scripts/` (see `scripts/README.md`): the chat analysis that builds the per-group CSVs and the page fetch. The URL enrichment and the duplicate merge were one-off steps and are not saved as scripts; the rules above are enough to recreate them.
- Resume with: `claude --continue`, then ask to start at step 4 (freemium and trial). Steps 1-3 are done.
