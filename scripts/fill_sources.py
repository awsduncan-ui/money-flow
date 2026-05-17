#!/usr/bin/env python3
"""
Walk money-flow-data.json and ensure every node has a `source` field.

The editorial rule: every node carries either (a) a real source citation, or
(b) a clear explanation of why no published source exists for that figure.

This script applies a lookup table for the common repeating sub-children
(wholesale gas, network costs, policy levies — identical across the six
energy trees) and a per-tree map for the supplier-specific nodes.

Run:
    python3 scripts/fill_sources.py            # apply changes
    python3 scripts/fill_sources.py --check    # just report gaps, don't write

Re-run safe: existing source fields are never overwritten.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "money-flow-data.json"

# Common sub-children that appear identically across every energy-supplier tree.
# Keyed on (parent_label, child_label) so labels can be reused safely elsewhere.
COMMON_ENERGY = {
    # Wholesale gas sub-children
    ("Wholesale gas", "Norwegian pipeline gas"):
        "DESNZ Digest of UK Energy Statistics (DUKES) Table 4.3 — UK natural-gas imports by country of origin (https://www.gov.uk/government/statistics/digest-of-uk-energy-statistics-dukes). Norway has been the UK's single largest gas source since 2022.",
    ("Wholesale gas", "UK Continental Shelf"):
        "DESNZ DUKES Table 4.1 — UK natural-gas production; North Sea Transition Authority (NSTA) field-level production data (https://www.nstauthority.co.uk/data-centre/data-downloads-and-publications/).",
    ("Wholesale gas", "LNG imports"):
        "DESNZ DUKES Table 4.3 (LNG imports by source country); National Gas Transmission entry-point flow data. Qatar and the US are the largest sources via Milford Haven (South Hook, Dragon LNG) and Isle of Grain terminals.",
    ("Wholesale gas", "Storage, balancing & trading"):
        "National Gas Transmission system operator monthly reports; Ofgem Wholesale Markets Indicators quarterly. Covers National Balancing Point trading, line-pack management and storage charges.",

    # Network sub-children — regulated, identical across suppliers
    ("Network costs", "Gas transmission"):
        "Ofgem RIIO-T2 final determinations for National Gas Transmission (price control period 2021-2026); sold by National Grid plc to a Macquarie-led consortium in early 2024 for ~£2.2bn equity. https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/network-price-controls-2021-2026-riio-2",
    ("Network costs", "Gas distribution"):
        "Ofgem RIIO-GD2 final determinations (2021-2026) for the four UK gas distribution networks: Cadent (largest), Northern Gas Networks, SGN, and Wales & West Utilities. Allowed revenues published per GDN annual report.",
    ("Network costs", "Metering & smart meter rollout"):
        "DESNZ Smart Metering Implementation Programme annual reports (https://www.gov.uk/government/collections/smart-meters-statistics); Ofgem price-cap methodology smart-meter net-cost component.",

    # Policy & social cost sub-children — statutory schemes, identical across suppliers
    ("Policy & social costs", "Energy Company Obligation (ECO4)"):
        "DESNZ ECO4 Order 2022 (Statutory Instrument 2022/875); Ofgem ECO administration annual reports (https://www.ofgem.gov.uk/environmental-and-social-schemes/energy-company-obligation-eco). Largest single component of energy-bill policy costs.",
    ("Policy & social costs", "Warm Home Discount"):
        "DESNZ Warm Home Discount Regulations 2022 (SI 2022/687). £150 rebate per eligible household over winter, recovered from suppliers and spread across all bill-payers.",
    ("Policy & social costs", "Green Gas Levy"):
        "DESNZ Green Gas Support Scheme Regulations 2021 (https://www.gov.uk/government/publications/green-gas-support-scheme-and-green-gas-levy). Funds biomethane injection into the gas grid.",
    ("Policy & social costs", "Other policy levies"):
        "Aggregate of smaller statutory levies and admin charges within the Ofgem cap's policy-cost component (capacity market admin, supplier-of-last-resort levies). Per-component breakdown not separately published; treated here as a residual.",
}

# Operating-cost sub-children. Same allowance structure across suppliers but the
# split between staff/IT/bad-debt/marketing/property is the supplier's choice,
# not the regulator's, and is illustrative rather than directly disclosed.
OPERATING_SOURCE_TEMPLATE = (
    "Illustrative breakdown of the Ofgem default-tariff-cap operating-cost allowance. "
    "The cap sets a total operating allowance per customer; the split between staff, IT, bad debt, "
    "marketing and property is the supplier's internal allocation and is not directly disclosed in "
    "this form. Numbers triangulate from {parent_co} annual report cost lines plus the Ofgem allowance methodology."
)

# Supplier-margin sub-children. The Ofgem cap sets a total EBIT allowance (~1.9%);
# how that profit gets split between corp tax / dividends / capex / exec pay / retained
# is the parent company's choice and is not directly published per-customer or per-UK-retail.
MARGIN_SOURCE_TEMPLATE = (
    "Illustrative allocation of the supplier-margin slice. {parent_co} reports group-level totals "
    "for tax, dividends, capex, executive pay and retained earnings; the share specifically "
    "attributable to UK retail-supply margin is not separately disclosed. Numbers reflect "
    "directional weighting based on each company's stated capital allocation."
)

# Per-supplier metadata for filling in {parent_co} placeholders
SUPPLIER_PARENT = {
    "british-gas":    "Centrica plc",
    "octopus-energy": "Octopus Energy Group Ltd",
    "eon-next":       "E.ON SE",
    "edf-energy":     "EDF SA",
    "ovo-energy":     "OVO Group Ltd",
    "scottish-power": "Iberdrola SA",
}

# Income-tax sub-children — Welfare and Health levels.
INCOME_TAX_SUBS = {
    ("Welfare", "Working-age benefits (Universal Credit etc.)"):
        "DWP Benefit Expenditure and Caseload Tables 2023-24 (https://www.gov.uk/government/collections/benefit-expenditure-tables); allocation within the Welfare category of HMRC's Annual Tax Summary.",
    ("Welfare", "Disability & incapacity benefits"):
        "DWP Benefit Expenditure and Caseload Tables — PIP, DLA, ESA and Attendance Allowance lines; HMRC Annual Tax Summary methodology.",
    ("Welfare", "Child & family benefits"):
        "HMRC Child Benefit Statistics; DWP residual tax credit caseload data; HMRC Annual Tax Summary Welfare sub-allocation.",
    ("Welfare", "Housing benefit (legacy)"):
        "DWP Housing Benefit Caseload Statistics; being absorbed into Universal Credit. Residual caseload is largely pensioners and supported-housing tenants.",
    ("Welfare", "Administration"):
        "DWP Annual Report and Accounts — operating cost lines; allocation within HMRC Annual Tax Summary Welfare category.",
    ("Health", "NHS front-line services"):
        "DHSC Annual Report and Accounts 2023-24; NHS England Annual Report. Front-line services include hospitals, primary care, community care, ambulance and mental health.",
    ("Health", "Adult social care (central contribution)"):
        "DHSC Annual Report — Better Care Fund and adult social care grant lines. Most adult social care is funded by local authorities via council tax and the social care precept; this is the central top-up only.",
    ("Health", "Public health"):
        "Office for Health Improvement and Disparities (OHID, formerly Public Health England) reporting; UK Health Security Agency annual report.",
    ("Health", "Medical research & training"):
        "NIHR (National Institute for Health and Care Research) annual report; Health Education England (now part of NHS England) workforce-training reporting.",
    ("Health", "NHS administration & arms-length bodies"):
        "DHSC ALB annual reports (NICE, CQC); NHS England HQ administration costs as published in NHS England annual report.",
}

# Top-level "Other / rounding" on income tax
INCOME_TAX_ROOT_CHILDREN = {
    "Other / rounding":
        "Reconciliation residual — HMRC Annual Tax Summary published category percentages don't sum to exactly 100% due to rounding and small unallocated items (transitional EU payments, minor lines). Treated here as a single 'Other' bucket so the tree totals correctly.",
}

# Coke-specific sources — many are illustrative because exact contract terms
# in the FMCG supply chain are commercially confidential.
COKE_SOURCES = {
    # Supermarket margin sub-children — speculative split
    ("Supermarket retailer margin", "Store operating costs (staff, lighting, refrigeration)"):
        "Illustrative — UK grocery retailers do not publish gross margin at SKU or category level. Component split estimated from industry analyst reports (IGD, Kantar) and the retailers' aggregate store-operating-cost disclosures.",
    ("Supermarket retailer margin", "Distribution from regional DC to store"):
        "Illustrative — supermarket internal logistics cost per SKU is not published. Estimated from the retailers' aggregate distribution-and-warehousing cost lines in their annual reports (Tesco, Sainsbury's, Asda).",
    ("Supermarket retailer margin", "Property & overheads"):
        "Illustrative — store property and head-office allocation. Estimated from the retailers' aggregate property cost lines (rent, business rates, depreciation).",
    ("Supermarket retailer margin", "Retailer operating profit"):
        "Illustrative — branded-soft-drink contribution to retailer profit is not separately disclosed. Tesco / Sainsbury's group operating margin (~3-5%) provides directional context but individual SKU profitability varies materially.",

    # CCEP cost-of-goods components — CCEP reports COGS as one line per segment
    ("Coca-Cola Europacific Partners (bottler)", "Aluminium can"):
        "Illustrative within CCEP's published COGS. CCEP discloses cost-of-sales as a single line in its segment results; the share attributable to aluminium-can purchases is estimated from LME aluminium prices and industry-reported can-making margins (Ball Corporation, Crown Holdings annual reports).",
    ("Coca-Cola Europacific Partners (bottler)", "Sugar, water, CO2 & labels"):
        "Illustrative within CCEP COGS. Sugar prices from British Sugar and Tate & Lyle; CO2 from industrial-gas market reports; water and label costs from CCEP segment cost commentary.",
    ("Coca-Cola Europacific Partners (bottler)", "Manufacturing & bottling labour"):
        "Illustrative within CCEP COGS / SG&A. CCEP discloses total employee costs in its annual report but not per-bottle attribution. Derived from CCEP UK headcount (~3,500) and reported pay.",
    ("Coca-Cola Europacific Partners (bottler)", "Distribution & logistics"):
        "Illustrative within CCEP cost lines. CCEP discloses aggregate distribution and warehousing costs in its annual report; per-can attribution is estimated from delivered-volume statistics.",
    ("Coca-Cola Europacific Partners (bottler)", "Sales, customer activation & local marketing"):
        "Illustrative within CCEP SG&A. CCEP discloses aggregate selling, general and administrative expenses; the marketing portion is estimated from CCEP investor presentations on marketing investment.",
    ("Coca-Cola Europacific Partners (bottler)", "Overheads & admin"):
        "Illustrative within CCEP SG&A. Head-office and group corporate cost allocation as reported in CCEP annual report.",

    # CCEP operating margin sub-children
    ("CCEP operating margin", "UK corporation tax (CCEP)"):
        "Statutory 25% UK corporation tax (from April 2023) on UK-attributable accounting profit. Per-margin share is illustrative because tax is a function of accounting profit (which includes group cost allocations) rather than operating margin.",
    ("CCEP operating margin", "Dividends to CCEP shareholders"):
        "CCEP dividend history (quarterly; ~$1.80/share annual run-rate FY2023) from CCEP investor relations. Per-margin attribution is illustrative — CCEP pays dividends from group profit, not a specific revenue line.",
    ("CCEP operating margin", "Capital expenditure & reinvestment"):
        "CCEP capex disclosure (~€800m group capex FY2023) per CCEP annual report. UK-attributable share illustrative.",
    ("CCEP operating margin", "Executive remuneration (CCEP)"):
        "CCEP Directors' Remuneration Report (NYSE-listed; full disclosure). Per-margin share is illustrative because executive pay is a fixed cost not proportional to a revenue line.",
    ("CCEP operating margin", "Retained for the business"):
        "Residual balancing figure — earnings retained on the balance sheet for future investment or volatility buffer.",

    # TCCC concentrate fee sub-children
    ("Concentrate fee to The Coca-Cola Company (TCCC)", "TCCC concentrate manufacturing & ingredients"):
        "Illustrative — TCCC reports concentrate operations at a high level in its 10-K. Concentrate ingredients (sweetener concentrate, flavourings, additives) are a small fraction of concentrate revenue; the high TCCC gross margin reflects this.",
    ("Concentrate fee to The Coca-Cola Company (TCCC)", "TCCC global marketing & brand investment"):
        "TCCC 10-K — marketing spend disclosed at company level (~$4bn/year). Per-can attribution is illustrative; TCCC's brand spend supports the whole portfolio, not just standard Coke.",
    ("Concentrate fee to The Coca-Cola Company (TCCC)", "TCCC R&D, overheads & corporate functions"):
        "TCCC 10-K — research and development and SG&A lines. Per-can attribution is illustrative.",

    # TCCC operating profit sub-children
    ("TCCC operating profit", "US federal & state corporation tax"):
        "TCCC effective tax rate from 10-K (typically 18-22% in recent years). Per-can attribution is illustrative because TCCC's tax is on global group profit, not a single product line.",
    ("TCCC operating profit", "Dividends to TCCC shareholders"):
        "TCCC dividend history (~$1.94/share FY2024, one of the longest unbroken dividend-increase streaks in US equities). Largest holders per TCCC proxy filing: Berkshire Hathaway, Vanguard, BlackRock.",
    ("TCCC operating profit", "Share buybacks"):
        "TCCC buyback authorisations and execution per 10-K filings. Per-can attribution is illustrative.",
    ("TCCC operating profit", "Capital expenditure & reinvestment"):
        "TCCC 10-K capex line — concentrate plants, R&D capex, capitalised brand investment.",
    ("TCCC operating profit", "Executive remuneration (TCCC)"):
        "TCCC DEF 14A proxy filings (annual; SEC EDGAR). CEO James Quincey total comp reported around $20-28m in recent years. Per-can attribution is illustrative — exec pay is fixed not proportional.",
    ("TCCC operating profit", "Retained for the business"):
        "Residual — earnings retained on TCCC balance sheet.",
}


def fill(node, ancestors, tree_id):
    """Recursively fill missing source fields. ancestors is a list of label strings."""
    if 'source' not in node:
        src = lookup_source(node['label'], ancestors, tree_id)
        if src:
            # Insert source in a sensible position (after label/share/xref, before children/note)
            new = {}
            for k in ('label', 'share', 'xref', 'category'):
                if k in node:
                    new[k] = node[k]
            new['source'] = src
            for k, v in node.items():
                if k not in new:
                    new[k] = v
            node.clear()
            node.update(new)
    for c in node.get('children', []):
        fill(c, ancestors + [node['label']], tree_id)


def lookup_source(label, ancestors, tree_id):
    """Find the right source for a node given its label, ancestor path, and tree id."""
    parent_label = ancestors[-1] if ancestors else None

    # Income tax root children (Other / rounding)
    if tree_id == 'income-tax' and parent_label == 'UK Income Tax':
        if label in INCOME_TAX_ROOT_CHILDREN:
            return INCOME_TAX_ROOT_CHILDREN[label]

    # Income tax Welfare / Health sub-children
    if tree_id == 'income-tax':
        key = (parent_label, label)
        if key in INCOME_TAX_SUBS:
            return INCOME_TAX_SUBS[key]

    # Coke tree specifics
    if tree_id == 'coke-can':
        key = (parent_label, label)
        if key in COKE_SOURCES:
            return COKE_SOURCES[key]

    # Energy supplier trees — common sub-children
    if tree_id in SUPPLIER_PARENT:
        key = (parent_label, label)
        if key in COMMON_ENERGY:
            return COMMON_ENERGY[key]

        parent_co = SUPPLIER_PARENT[tree_id]

        # Operating-cost sub-children — same pattern across suppliers
        if parent_label == 'Operating costs':
            return OPERATING_SOURCE_TEMPLATE.format(parent_co=parent_co)

        # Supplier-margin sub-children — same pattern across suppliers
        if parent_label and 'Supplier margin' in parent_label:
            return MARGIN_SOURCE_TEMPLATE.format(parent_co=parent_co)

    return None  # Caller will report this and leave the node alone


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true',
                   help='just report what would change, do not write')
    args = p.parse_args()

    data = json.loads(DATA_FILE.read_text())

    # Pass 1: report gaps before
    gaps_before = collections.Counter()
    for t in data['trees']:
        report_gaps(t['root'], [], t['id'], gaps_before)

    # Apply fills
    for t in data['trees']:
        fill(t['root'], [], t['id'])

    # Pass 2: report gaps after
    gaps_after = collections.Counter()
    for t in data['trees']:
        report_gaps(t['root'], [], t['id'], gaps_after)

    print(f"Source gaps before: {sum(gaps_before.values())}")
    print(f"Source gaps after:  {sum(gaps_after.values())}")
    if gaps_after:
        print("\nRemaining gaps (no rule matched — add to fill_sources.py):")
        for (tree_id, parent, label), n in gaps_after.most_common():
            print(f"  [{tree_id}] {parent} > {label}")

    if args.check:
        print("(--check: not writing)")
        return 0

    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {DATA_FILE.relative_to(REPO_ROOT)}")
    return 0


def report_gaps(node, ancestors, tree_id, counter):
    if 'source' not in node:
        counter[(tree_id, ancestors[-1] if ancestors else None, node['label'])] += 1
    for c in node.get('children', []):
        report_gaps(c, ancestors + [node['label']], tree_id, counter)


if __name__ == '__main__':
    sys.exit(main())
