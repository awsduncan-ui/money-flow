# Money Flow

A web-based tracer for the hidden flow of money through society.

Enter an amount you've paid — income tax, an energy bill, eventually anything else — and see where that money goes. Click any line to drill in: tax → welfare → disability benefits, or energy bill → supplier margin → executive pay, dividends, corporation tax. Every node carries a source so claims can be traced.

Live at: **https://awsduncan-ui.github.io/money-flow/** *(after Pages is enabled)*

## What's in here

- `index.html` — single-file app. Vanilla JavaScript, no framework, no build step. Has a bundled copy of the data so it works opened locally.
- `money-flow-data.json` — canonical data. Trees, percentages, notes, sources, and the UK National Minimum Wage benchmark used for pay-ratio comparisons. Fetched by the page at load time.

The page tries to fetch `money-flow-data.json` on load. If it succeeds (when served over HTTP) it uses the live JSON; if it fails (typically when opened as a local file due to browser CORS rules) it falls back to the bundled copy in the HTML. A small indicator at the top of the page shows which mode is active.

## Currently modelled

- **UK Income Tax** — 15-way split from HMRC's Annual Tax Summary; welfare and health drill one level deeper. Other branches are stubbed.
- **British Gas — annual gas bill** — Ofgem default-tariff-cap cost stack (wholesale / network / operating / policy / margin / VAT / other), with the supplier margin broken down into corporation tax, dividends, capex, executive pay, retained earnings. Wholesale, network, operating and policy branches drill one level deeper.

## Data shape

A tree is a `FlowNode`:

```js
{
  label:    'Welfare',           // displayed name
  share:    0.237,               // fraction of parent (root has no share)
  source:   'DWP / HMT PESA',    // citation, displayed as a small caption
  note:     '...',               // optional one-paragraph explanation
  children: [ ... ],             // optional — nodes without children are leaves
  payRatio: { ... }              // optional — see below
}
```

A `payRatio` block renders as a highlighted callout under the node, computed against the UK National Minimum Wage:

```js
payRatio: {
  label:   'Name, Role — FY single figure',
  amount:  8200000,
  caveats: 'optional source/verification note'
}
```

The multiple is computed at render time as `amount / uk_nmw_annual`, so a single NMW update at the top of the JSON flows through every executive figure in the app.

## Editorial principles

1. **Sources beat precision.** Better a directional figure with a clear source line than a polished number from nowhere.
2. **Stubs are honest.** Branches we haven't yet modelled show "— end of trace —" rather than fabricating a breakdown.
3. **Cross-references will matter.** VAT and corporation tax already appear inside the gas-bill tree; eventually clicking them should jump into the income-tax tree at the right amount.
4. **NMW is the common denominator.** Executive pay is shown as a multiple of the National Minimum Wage rather than company-specific quartiles — universal, transparent, easy to update.

## Roadmap

- [ ] Cross-tree links — clicking VAT or corporation tax jumps into the income-tax tree
- [ ] More suppliers — at minimum Octopus, EDF, OVO so we can compare cost stacks
- [ ] More item types — mortgage payment, rent, supermarket spend, a coffee, a Spotify subscription
- [ ] Automated data refresh via GitHub Actions — scrape NMW from gov.uk, Ofgem cap data quarterly, regenerate `money-flow-data.json`
- [ ] A "Pay ratios" view across the whole app, sorted by multiple
- [ ] Paste-a-statement mode: parse a bank-statement CSV and tag each line

## Local development

Open `index.html` directly in a browser — it works, using bundled data. For the live-fetch path, serve the folder:

```bash
cd ~/Code/money-flow
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Data updates

For now, manual. Edit `money-flow-data.json` and bump the `updated` field. Eventually a GitHub Action will regenerate this from the canonical sources (gov.uk for NMW, HMRC tax summary, Ofgem cap publications, company annual reports).

## License

MIT — see `LICENSE`.
