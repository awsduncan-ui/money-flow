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

- **UK Income Tax** — HMRC Annual Tax Summary, FY 2022-23 basis. 15 top-level categories. Welfare and Health drill one level deeper.
- **British Gas — annual gas bill** — Ofgem default-tariff-cap cost stack (wholesale / network / operating / policy / margin / VAT / other). Wholesale, network, operating, policy all drill one level deeper. Supplier margin breaks down into corporation tax, dividends to shareholders, capex, executive remuneration (Centrica CEO, with NMW multiple), retained earnings.
- **Octopus Energy — annual gas bill** — Same Ofgem cap shape (because it's the same regulated structure), with a deliberately contrasting supplier-margin branch: privately held (no FTSE dividend; investors are Generation IM, CPP Investments, Tokyo Gas, KKR), heavier reinvestment weighting (Kraken platform + Octopus Energy Generation), lower executive pay. Pay-ratio panel intentionally omitted on Greg Jackson pending verification from Companies House.

## Editorial principles

1. **Sources beat precision.** A directional figure with a clear citation beats a polished number from nowhere.
2. **Stubs are honest.** Branches we haven't modelled show "— end of trace —" rather than fabricating a breakdown.
3. **Pay against NMW.** Executive remuneration is always shown as a multiple of the UK National Minimum Wage. Universal, statutory, transparent, single-point-of-update.
4. **Caveats inline.** Big-claim figures (CEO pay, contested allocations) carry a verification note inline so a reader knows where to push back.
5. **No demo magic at the expense of truth.** Better to model fewer things accurately than many things speculatively.

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
- [ ] **Cross-tree links** — click VAT or corporation tax inside a gas-bill tree and jump into the income-tax tree at the right amount. The moment "everything connects" becomes visible. Add an `xref` field on nodes; the UI switches tree and seeds the input amount.
- [ ] **Verify Greg Jackson's compensation** from Octopus Energy Group Ltd's most recent Companies House accounts, then add a `payRatio` block on the executive-remuneration node.
- [ ] **Verify FY 2022-23 income-tax figures** against the latest HMRC Annual Tax Summary publication and bump to the most recent published year.
- [ ] **Validate shares sum to ~1** in CI on every commit. Cheap safety net.
- [x] ~~**Octopus Energy as second supplier**~~ — added 2026-05-11. See below.

### More item types to model
- [ ] Mortgage payment (interest + capital + securitisation chain → MBS investors)
- [ ] Rent (private landlord vs housing association vs council — different cost stacks)
- [ ] Supermarket weekly shop (food cost, labour, supermarket margin, supplier margins, ag subsidy interactions)
- [ ] A coffee at Starbucks (beans, dairy, rent, labour, royalties, tax — the original example from the conversation)
- [ ] A Spotify / Netflix subscription (royalties, label/studio cut, infrastructure, profit)
- [ ] A pint at the pub (beer cost, duty, VAT, pub margin, brewery margin)
- [ ] Council tax (services breakdown by local authority — needs postcode input)
- [ ] Pension contribution (where does it actually get invested?)

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

## Collaboration

- Ali edits and pushes.
- Ali's friend views via the GitHub Pages URL — no GitHub account needed.
- Commits authored as `awsduncan-ui <awsduncan-ui@users.noreply.github.com>` with a Claude co-author line. Switch to plain attribution by adjusting the `-c user.name`/`user.email` flags on commits, or removing the Co-Authored-By trailer.
