# Money Flow — Project Log

A running record of what we're building, why, and what's planned. Working document for the team; also a handoff doc for fresh sessions (mine or anyone else's) so context isn't lost.

## The idea

A web tracer for where money flows through society. You input an amount you've paid — income tax, an energy bill, eventually anything else — and the app shows where it goes. Every line drills down. Tax → welfare → disability benefits. Energy bill → supplier margin → executive pay → multiple of National Minimum Wage. Every node has a citation.

The thesis is that the flow of money in modern economies is largely opaque, even though most of the source data is technically public. The app exists to make that flow visible and traceable.

## Where it lives

- **Repo:** https://github.com/awsduncan-ui/money-flow (public)
- **Live site:** https://awsduncan-ui.github.io/money-flow/
- **Local checkout:** `~/Code/money-flow/`
- **Old standalone copy:** `~/Desktop/money-flow.html` — now stale, can be deleted whenever

## Architecture

Single-page vanilla-JS app. No framework, no build step.

```
index.html                  UI + bundled fallback data
money-flow-data.json        Canonical data, fetched at load time
scripts/update_nmw.py       Refreshes the NMW figure from gov.uk
.github/workflows/          GitHub Actions to run the refresh on a schedule
```

The page tries `fetch('./money-flow-data.json')` on load. Success → live data. Failure (typically when the file is opened directly as `file://` due to browser CORS rules) → bundled fallback. A status line at the top of the page shows which mode is active.

## Data model

A node is a `FlowNode`:

```js
{
  label,        // displayed name
  share,        // fraction of parent (root has none)
  source,       // optional — citation, shown as a small caption
  note,         // optional — one-paragraph explanation
  children,     // optional — leaf if absent
  payRatio      // optional — see below
}
```

A `payRatio` block renders as a callout, computed against the UK National Minimum Wage:

```js
{
  label,        // 'Name, Role — FY single figure'
  amount,       // gross annual £
  caveats       // optional
}
```

The multiple is computed at render time as `amount / uk_nmw_annual`. NMW lives at the top of the JSON file. A single annual update there flows through every executive figure in the app automatically.

## Currently modelled

Each tree now carries a `category` field: `tax`, `energy`, or `consumer`. The compare-mode view filters on `category === 'energy'` so it doesn't sweep in unrelated trees.

- **UK Income Tax** *(category: tax)* — HMRC Annual Tax Summary, FY 2022-23 basis. 15 top-level categories. Welfare and Health drill one level deeper.
- **Six UK energy suppliers — annual gas bill** *(category: energy)* — All share the same top-level Ofgem default-tariff-cap shape (because the cap is regulatory and identical for every supplier). The interesting differentiation is in each supplier-margin branch:
  - **British Gas** — Centrica plc (FTSE 100). Dividends to public shareholders (BlackRock, Vanguard, L&G via pension funds). CEO Chris O'Shea ~£8.2m, shown as multiple of NMW.
  - **Octopus Energy** — Privately held. Investors: Generation IM, CPP Investments, Tokyo Gas, KKR. No FTSE dividend. Heavier capex weighting (Kraken + Octopus Energy Generation). Greg Jackson pay TBD.
  - **E.ON Next** — UK arm of E.ON SE (Germany, DAX 40). Built on Kraken (licensed from Octopus). Dividends include RAG-Stiftung (German foundation for legacy coal-mining liabilities).
  - **EDF Energy** — UK arm of EDF SA, 100% French state-owned since 2023 renationalisation. Supplier margin ultimately accrues to the French Treasury. Group CEO pay capped under French state rules. Operates UK nuclear fleet.
  - **OVO Energy** — UK private. Founder Stephen Fitzpatrick, Mitsubishi Corp ~20% stake. Took SSE retail 2020. Heavy retained-earnings weighting for SSE integration.
  - **Scottish Power** — UK arm of Iberdrola SA (Spain, IBEX 35). QIA largest shareholder. Major UK wind portfolio. One of Europe's highest-paying utility-CEO packages at group level.
- **A can of Coke** *(category: consumer)* — A 330ml can from a UK supermarket at a representative 85p. Top-level shape: VAT (17%) → income-tax, Sugar Tax/SDIL (9%) → income-tax, supermarket margin (15%), Coca-Cola Europacific Partners (59%). Inside CCEP: the famous concentrate-fee line flowing to The Coca-Cola Company in Atlanta, plus aluminium-can cost, raw materials, distribution, marketing, CCEP operating margin (which drills further into UK corp tax, dividends to Olive Partners + TCCC + free float, capex, exec pay). The TCCC concentrate fee drills further into US tax, TCCC dividends (Berkshire Hathaway ~9%, Vanguard, BlackRock), buybacks, and James Quincey's executive pay. Headline figures (VAT, SDIL) are firm; the deeper cost-component splits are illustrative because exact contract terms are commercially confidential.
- **A coffee from Starbucks** *(category: consumer)* — A representative £4 grande latte at a UK Starbucks. Top-level: VAT (17%) → income-tax, cost of goods (13%, drills into beans/milk/cup/syrups/wastage), store operating costs (45%, drills into labour/rent/utilities/depreciation/cleaning/overheads — the big one), UK head office (7%), royalty to Starbucks Corp (5%, the famous tax-controversy slice — drills into Starbucks Corp's US operating profit, US tax, dividends, buybacks, capex, Brian Niccol's record-setting first-year CEO package), UK corporation tax (3%) → income-tax, residual UK operating profit (10%). The Niccol pay-ratio is the most striking single figure across the app — ~£89m total FY2025 package against £24,780 NMW is ~3,600× — with a clear caveat that the bulk is one-off sign-on equity replacing his Chipotle awards.
- **Cross-tree links** — VAT and Corporation Tax inside every energy-bill tree, plus VAT/SDIL/UK corp tax inside the Coke tree, are clickable: they jump into the UK Income Tax tree with the appropriate amount as the new root, completing the "everything connects" thesis.
- **Compare-energy-suppliers view** — Single ⇄ Compare toggle. Compare mode shows all six energy trees side by side at top level, plus their differing supplier-margin breakdowns. The visual makes the point: top-level is identical (Ofgem); supplier-margin is where the money goes differently. Filter is `category === 'energy'` so non-energy trees (income-tax, Coke, future consumer items) don't pollute the view.

## Editorial principles

1. **Sources beat precision.** A directional figure with a clear citation beats a polished number from nowhere.
2. **Every node carries a source field.** Either a real citation (with URL where stable), or an explicit explanation of why no published source exists for that figure (e.g. "Illustrative — supermarkets don't disclose category-level margins"). Audited and enforced by `scripts/fill_sources.py`; the script reports any node missing a `source` field and exits non-zero in `--check` mode so it can be wired into CI later.
3. **Stubs are honest.** Branches we haven't modelled show "— end of trace —" rather than fabricating a breakdown.
4. **Pay against NMW.** Executive remuneration is always shown as a multiple of the UK National Minimum Wage. Universal, statutory, transparent, single-point-of-update.
5. **Caveats inline.** Big-claim figures (CEO pay, contested allocations) carry a verification note inline so a reader knows where to push back.
6. **No demo magic at the expense of truth.** Better to model fewer things accurately than many things speculatively.

## Design language

- Dark, journalistic. Near-black background (`#0a0a0c`), sodium-amber accent (`#d4a04a`) for money figures, cool slate (`#8aa4b3`) for interactive elements.
- Serif for prose (Georgia), tabular monospace for figures (SF Mono / Menlo).
- Subtle radial glow at top of page. No icons, no chartjunk.

## Automation

| Source                              | Cadence            | Method                                                    | Status     |
| ----------------------------------- | ------------------ | --------------------------------------------------------- | ---------- |
| UK National Minimum Wage            | Annual (April)     | gov.uk scrape via `scripts/update_nmw.py`, run weekly     | ✅ live     |
| Ofgem default tariff cap            | Quarterly          | TBD — different parser, similar workflow shape            | 🚧 planned |
| HMRC Annual Tax Summary             | Annual (autumn)    | TBD — will likely need PDF parsing                        | 🚧 planned |
| Company executive pay               | Annual             | Manual update from Annual Reports                         | 📌 manual  |
| Centrica annual report figures      | Annual             | Manual                                                    | 📌 manual  |

### How the NMW refresh works

1. `scripts/update_nmw.py` curls `https://www.gov.uk/national-minimum-wage-rates`
2. Anchors on the `current-rates` URL fragment to scope the search to the current rates table (avoiding the historic-rates table further down)
3. Picks the first `£X.XX` after that anchor — the 21+ column is leftmost in the table, so it's the right value
4. Computes the annual full-time figure (rate × 37.5h × 52wk) and rounds to the nearest £10
5. Surgically updates three fields in `money-flow-data.json` (`uk_nmw_annual`, `uk_nmw_basis`, `updated`) and the matching fields in `index.html`'s BUNDLED_DATA — preserves all other formatting
6. The workflow runs on schedule + manual dispatch, commits if anything changed, pushes back to `main`
7. If parsing fails (e.g. gov.uk redesigns the page) the script raises, the workflow fails, and you get an email — better than silently shipping wrong data

## Roadmap

### Next up
- [ ] **Verify executive remuneration figures and add payRatio blocks** for Greg Jackson (Octopus), Chris Norbury (E.ON Next UK), the relevant EDF UK CEO, Stephen Fitzpatrick (OVO), and Keith Anderson (Scottish Power) — most are stubbed pending verification because either the parent's disclosure isn't FTSE-style "single figure", or only the group CEO's number is public (which conflates UK and global responsibility). Octopus's latest accounts (PDF on Companies House, filed 09 Jan 2026, FY ending April 2025, 92 pages, image-only — requires OCR or manual lookup) are the priority since Octopus is Ali's own supplier.
- [ ] **Smaller/niche energy suppliers** — Utilita (prepayment specialist), Ecotricity (private, Dale Vince), Good Energy (public, AIM-listed, ~120k customers, green-tariff focus), So Energy (owned by ESB, Irish state), Outfox the Market, plus a handful of regional / community-owned suppliers. Each deserves an editorial pass for its specific ownership and pay disclosure rather than being batched.
- [ ] **Verify FY 2022-23 income-tax figures** against the latest HMRC Annual Tax Summary publication and bump to the most recent published year.
- [ ] **Validate shares sum to ~1** in CI on every commit. Cheap safety net.
- [ ] **Visual indicator on cross-tree jumps** — when you arrive in a tree via an xref click, show a subtle "← from British Gas / VAT" breadcrumb prefix so users know how they got there.
- [x] ~~**Cross-tree links**~~ — added 2026-05-12. VAT and Corporation Tax in every energy tree jump into the income-tax tree.
- [x] ~~**Compare-suppliers mode**~~ — added 2026-05-12. Single ⇄ Compare toggle.
- [x] ~~**Octopus Energy as second supplier**~~ — added 2026-05-11.
- [x] ~~**Add the rest of the Big-Six majors**~~ — E.ON Next, EDF, OVO, Scottish Power added 2026-05-12.

### More item types to model
- [ ] Mortgage payment (interest + capital + securitisation chain → MBS investors)
- [ ] Rent (private landlord vs housing association vs council — different cost stacks)
- [ ] Supermarket weekly shop (food cost, labour, supermarket margin, supplier margins, ag subsidy interactions)
- [x] ~~A coffee at Starbucks~~ — added 2026-05-12. The Brian Niccol pay-ratio is the most striking figure across the app.
- [ ] A Spotify / Netflix subscription (royalties, label/studio cut, infrastructure, profit)
- [ ] A pint at the pub (beer cost, duty, VAT, pub margin, brewery margin)
- [ ] Council tax (services breakdown by local authority — needs postcode input)
- [ ] Pension contribution (where does it actually get invested?)
- [x] ~~A can of Coke~~ — added 2026-05-12 as the first `consumer` category tree.

### Bigger features
- [ ] **Paste-a-statement mode** — upload a bank statement CSV, auto-categorise each line, show "where my month went" in aggregate
- [ ] **Pay-ratios view** — list every executive across every modelled company, sorted by multiple of NMW. The ranking itself becomes the headline.
- [ ] **Cross-references that flow money back into other trees** — VAT and corporation tax in gas bill → into income-tax tree. Handle recursion without infinite loops.
- [ ] **Compare-suppliers mode** — pick two suppliers and view their cost stacks side by side, highlighting where the supplier-margin breakdown differs
- [ ] **Postcode / region awareness** — for items where location matters (council tax, regional gas distribution network, public transport subsidies)

### Infrastructure
- [ ] Ofgem cap quarterly refresh (different parser, similar workflow)
- [ ] HMRC tax summary annual refresh (will likely need PDF parsing — try `pdfplumber`)
- [ ] "Freshness" indicator on each node showing when its underlying data was last verified
- [ ] Light test suite — share-sum validation, JSON schema validation, link checks on source URLs

## Decisions and their reasoning

### Why dark UI?
The thesis is "exposing the hidden flow of money". Dark UI matches the voice. Sodium-amber accent (rather than the obvious gold or green) reads as investigative/journalistic rather than fintech-y.

### Why NMW for executive pay, not lower-quartile?
We originally used lower-quartile pay from companies' published disclosure (Centrica's 2023 lower-quartile ratio: ~191×). But:
- Data isn't consistently available across companies
- "Lower quartile of company X" is opaque to a reader without context
- It under-states the gap, because at a place like Centrica the lower quartile is still ~£40k (skilled engineer territory), not the actual floor of UK employment
- It needs new company-specific data every time we add a new firm

NMW is universal, statutory, public, updates predictably each April, and lets us show one comparable multiple for every executive at every company.

### Why a bundled HTML fallback?
The page should still work if opened locally as a file (where `fetch()` is blocked by browser CORS). The bundled copy is a minimal version of the data — enough to render the structure. It gets stale over time, but the NMW refresh workflow updates the BUNDLED_DATA NMW values too, which is the most important moving figure.

### Why GitHub Pages?
Free, public, zero infrastructure, plays nicely with Actions for the data automation. Site is read-only for visitors; all data updates go through commits to the repo.

### Why stdlib-only for the scraper?
Removes any dependency-installation step. `curl` is everywhere (macOS, Linux, CI). Python ships everywhere. No `requirements.txt`, no version-pinning headaches. If the script grows past what stdlib + curl can do, we'll reconsider.

### Why scrape vs. use an API?
None of our data sources (gov.uk, HMRC, Ofgem, company annual reports) publish a public JSON API. So scraping is the only option until they do.

## Sessions log

A brief log of what changed each working session, so a fresh session can catch up quickly.

### 2026-05-10
- Initial prototype as `~/Desktop/money-flow.html`. UK Income Tax only, hand-written tree structure, dark palette established.

### 2026-05-11
- Added British Gas annual gas bill tree on Ofgem cap structure.
- Added Centrica supplier-margin breakdown including executive remuneration.
- Added `payRatio` field. Initially used company lower-quartile pay; then switched universally to UK NMW as the denominator with a single constant.
- Split data into separate `money-flow-data.json`; HTML now fetches it with a bundled fallback for local file use.
- Moved project from Desktop to `~/Code/money-flow/`. Initialised git, created public GitHub repo, enabled GitHub Pages at https://awsduncan-ui.github.io/money-flow/.
- Built NMW auto-refresh: `scripts/update_nmw.py` (stdlib + curl) and `.github/workflows/refresh-data.yml` (weekly + manual dispatch). First run picked up the April 2026 rate (£12.71/hr → £24,780/yr), replacing the previously hardcoded April 2025 figure.
- Added **Octopus Energy** as a third tree — Ali's own supplier. Same Ofgem cap top-level shape as British Gas (because every UK supplier is governed by the same regulated stack), with deliberately contrasting supplier-margin branch: privately held (no FTSE dividend), heavier reinvestment weighting, different investor set (Generation IM, CPP Investments, Tokyo Gas, KKR), lower exec pay. Pay-ratio for Greg Jackson left as a stub pending verification from Companies House. Bundled fallback in `index.html` extended to match.

### 2026-05-12 (late night)
- Added a **coffee from Starbucks** tree — second consumer-category item, modelled on the recurring "what does this product/service cost actually pay for" structure. Top-level slices: VAT, cost-of-goods (with the famous reveal that the actual coffee beans are among the smallest line items), store operating costs (the biggest single slice, dominated by labour and rent), UK head office, the marquee royalty-to-Starbucks-Corp slice, UK corp tax, and a residual UK operating profit (which has often been low or negative thanks to the royalty / intercompany cost structure). Includes the Public Accounts Committee 2012 inquiry context — Starbucks UK paid only £8.6m UK corporation tax over 14 years on £3bn+ sales, largely via the Netherlands royalty arrangement. Drills further into Starbucks Corp's US economics: tax, dividends, buybacks, capex, and **Brian Niccol's record-setting first-year CEO package** (~$113m / ~£89m total FY2025, mostly one-off sign-on equity replacing Chipotle awards — pay-ratio shows ~3,600× NMW for the sign-on year, with explicit caveat that ongoing target compensation is much lower (~£13m → ~530× NMW)). The most editorially loaded single tree so far.

### 2026-05-12 (night)
- **Collapsed the six gas-supplier pills into one "Gas bill" pill with a supplier dropdown.** Ali's feedback: 8 pills in the tree-selector was too busy. Introduced a `group` field on trees — trees sharing a `group` render as a single pill in the tree-selector (using a `GROUP_LABELS` lookup for the display name); when one of them is active, the input row gains a `<select>` dropdown to switch between siblings. State stays simple — `currentTreeIdx` still points at a specific tree, the dropdown just toggles which one. Switching via the dropdown preserves `baseAmount` (the bill amount the user has already typed) rather than resetting it, which is the right behaviour because the same £-amount applies to every supplier.
- Compare mode untouched (still iterates `category === 'energy'`).
- Supplier `label` fields simplified from "British Gas — gas bill" to "British Gas" (now used as dropdown option labels; the gas-bill context comes from the pill). Each supplier's `promptSuffix` simplified from "with British Gas" to "with" because the supplier name now lives in the dropdown that follows.
- BUNDLED_DATA in index.html updated to match so offline fallback works the same way.

### 2026-05-12 (late evening)
- **Source-coverage audit and fill.** Audited every node in every tree against the principle that "every node carries a source field". 161 of 238 nodes lacked one — almost entirely repeated sub-children that appear identically across the six energy trees (wholesale gas, network costs, policy levies) plus the executive-pay-split children. Built `scripts/fill_sources.py` with a lookup table keyed on `(parent_label, child_label)` and per-tree fall-through rules, applied to fill all 161 gaps in one pass. The script is idempotent and re-runnable (existing sources are never overwritten), exits non-zero in `--check` mode if any gaps remain — could be wired into CI to enforce the principle for new nodes.
- Also strengthened root-level sources on every tree with stable URLs (HMRC Annual Tax Summary, Ofgem price-cap page, each company's investor relations or Companies House page).
- Strengthened the **Coke price source** specifically per Ali's call-out: the root `source` field now explicitly explains there's no single authoritative source for a "UK average can price" (ONS CPI tracks at category not SKU level, Coke doesn't publish RRP), explains the 85p default is a representative 2025-26 single-can supermarket figure based on observed Tesco/Sainsbury's pricing, and gives the realistic range (75p–£1.20).
- A note on JSON formatting: the source-fill script writes with `json.dumps(..., indent=2)` which expanded previously-inline child objects (e.g. `{ "label": "X", "share": 0.5, "note": "..." }`) onto separate lines. The file is now ~1,640 lines vs ~620 before; the change is purely cosmetic and the NMW auto-refresh script still parses and writes the file correctly.
- A note on bundled fallback: BUNDLED_DATA in index.html still carries no sources or notes (just structure + shares + xref + payRatio). This is a deliberate trade-off — keeps the bundled fallback lean for `file://` users. The data-status line ("Offline · bundled data") makes the limitation visible. Documenting here in case we want to revisit.

### 2026-05-12 (evening)
- Added a **can of Coke** tree — first consumer-goods item. Tracked the chain from supermarket shelf back through HMRC (VAT + Sugar Tax via cross-tree links), the supermarket margin, Coca-Cola Europacific Partners as the bottler, and the concentrate fee flowing to The Coca-Cola Company in Atlanta. The TCCC operating profit drill-down — through US tax, dividends to Berkshire Hathaway / Vanguard / BlackRock, buybacks — is the first non-UK money-flow modelled in the app, and a useful proof that the tree structure handles multinational supply chains.
- Introduced a **`category` field on every tree** (`tax`, `energy`, `consumer`). Necessary because the `isEnergyTree` filter for compare-mode was previously "everything except income-tax", which would have incorrectly swept the Coke tree into compare-suppliers view. Now it filters cleanly on `category === 'energy'`. Future categories: `housing`, `transport`, `subscription` etc. as more item types are added.
- Improved the **input step calculation** to handle sub-£10 amounts — now scales from £100 step (≥£1000) down to £0.05 step (<£1). Necessary so the up/down arrows on the Coke input nudge by 5p rather than £50.
- Fixed preset rendering: switched `'£' + v.toLocaleString('en-GB')` to `fmtMoney(v)` so £1.20 doesn't render as "£1.2".
- Renamed compare-mode button to **"⇄ Compare energy suppliers"** for accuracy.

### 2026-05-12 (afternoon)
- Added a **stacked proportional flow bar** above each level in both single and compare views. Decided against a pie chart after weighing it: pie wedges become unreadable below ~3% (many income-tax categories sit there), are hard to compare at similar sizes, and don't compose well across drill-downs. Stacked horizontal bar gives the same proportional reading, scales to many categories, is mobile-friendly, and lets the existing list stay as the legend. Segments cycle through four opacity shades so adjacent slices distinguish; xref segments use the slate accent so cross-tree links read as "leaves this tree" at a glance. Hover on a bar segment highlights the matching row; clicking a segment fires the row's click handler (drill or jump).

### 2026-05-12 (morning)
- Attempted **Greg Jackson Companies House lookup**: pulled the latest Octopus Energy Group Ltd accounts (filed 09 Jan 2026, FY ending 30 April 2025, 92 pages) from filing-history endpoint MzQ5ODI3MjQyMWFkaXF6a2N4. PDF is image-only — neither `pypdf` nor `pypdfium2` extract any text. Marked as a manual-OCR task; could be done with Tesseract or by Ali eyeballing the Directors' Remuneration Report section.
- Built **cross-tree links** via a new `xref` field on `FlowNode`. Added to VAT and Corporation Tax in every energy-bill tree. Clicking such a node calls `jumpToTree(treeId, amount)` — switches to the target tree, seeds `baseAmount` with the carry-through amount, resets the path. Visual: a slate-coloured `↗ Target Tree Name` arrow distinguishes xref nodes from drill-in chevrons; hover turns amber. Bundled fallback updated.
- Built a **Compare suppliers** view. View-toggle button next to the data-status line switches between Single trace and ⇄ Compare suppliers. Compare renders one card per energy tree showing top-level rows (label, amount, %) plus the supplier-margin children breakdown inline. Clicking a card title jumps back into single mode focused on that supplier. The visual reinforces the editorial point — top-level is identical (Ofgem), supplier-margin is where the differentiation lives.
- Added four more UK suppliers as full trees: **E.ON Next** (E.ON SE, German DAX-listed, Kraken-licensee), **EDF Energy** (EDF SA, 100% French state-owned post-2023 renationalisation, lead UK nuclear operator), **OVO Energy** (UK private, Stephen Fitzpatrick + Mitsubishi Corp, integrated SSE retail 2020), **Scottish Power** (Iberdrola SA, Madrid IBEX 35, major wind portfolio). Each gets the full Ofgem cap structure with sub-children for wholesale / network / operating / policy, plus a distinct supplier-margin branch reflecting parent-company ownership and capital allocation. Pay-ratio panels stubbed across all four pending verification of each UK CEO's compensation. Bundled fallback in `index.html` extended to match.
- Updated footer note to mention compare mode and xref behaviour. PROJECT_LOG roadmap updated: completed items struck, "smaller / niche suppliers" added as a future editorial pass rather than rushed in this turn.

## Collaboration

- Ali edits and pushes.
- Ali's friend views via the GitHub Pages URL — no GitHub account needed.
- Commits authored as `awsduncan-ui <awsduncan-ui@users.noreply.github.com>` with a Claude co-author line. Switch to plain attribution by adjusting the `-c user.name`/`user.email` flags on commits, or removing the Co-Authored-By trailer.
