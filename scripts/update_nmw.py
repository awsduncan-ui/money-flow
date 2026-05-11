#!/usr/bin/env python3
"""
Refresh the UK National Minimum Wage figure in money-flow-data.json
from the canonical source (gov.uk).

Standard library only — no pip install required.

Run locally:
    python3 scripts/update_nmw.py

In CI: see .github/workflows/refresh-data.yml

The script is intentionally noisy. If gov.uk's page structure ever changes
and parsing breaks, the script raises rather than guessing — better a failing
workflow (which emails you) than silently-wrong data.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

NMW_PAGE_URL = "https://www.gov.uk/national-minimum-wage-rates"
FULL_TIME_HOURS_PER_WEEK = 37.5
WEEKS_PER_YEAR = 52

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "money-flow-data.json"
INDEX_FILE = REPO_ROOT / "index.html"


def fetch(url: str) -> str:
    """
    Fetch a URL via the system curl. We use curl rather than urllib because the
    python.org Python distribution on macOS ships without a system cert bundle,
    so urllib HTTPS fails locally; curl works everywhere we run (macOS, Ubuntu CI).
    """
    result = subprocess.run(
        [
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--max-time", "30",
            "--user-agent", "money-flow-bot/0.1 (+https://github.com/awsduncan-ui/money-flow)",
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"curl failed (exit {result.returncode}) fetching {url}: {result.stderr.strip()}"
        )
    return result.stdout


def extract_nlw_rate(html: str) -> float:
    """
    Find the current 21-and-over rate (National Living Wage) in £/hour on gov.uk.
    Returns a float, e.g. 12.71.

    Strategy: anchor on the "current-rates" section fragment (gov.uk uses this
    as the anchor for the current-rates heading and table). Within that section,
    the first £X.XX is the 21-and-over rate (leftmost data column in the table).
    The page also contains a "Previous rates" table further down which we must
    not pick up — anchoring on "current-rates" guarantees we don't.

    Raises RuntimeError if the page can't be parsed — better than guessing.
    """
    flat = re.sub(r"\s+", " ", html)

    current_section = re.search(
        r"current-rates(.{0,3000})",
        flat,
        re.IGNORECASE | re.DOTALL,
    )
    if not current_section:
        raise RuntimeError(
            f"Could not find 'current-rates' anchor on {NMW_PAGE_URL}. "
            "Page structure may have changed."
        )
    scope = current_section.group(1)

    rate_match = re.search(r"£(\d+(?:\.\d{2})?)", scope)
    if not rate_match:
        raise RuntimeError(
            f"Found 'current-rates' section but no £ amount inside. "
            "Page structure may have changed — inspect and update extract_nlw_rate()."
        )

    raw = rate_match.group(1)
    return float(raw) if "." in raw else float(raw)  # tolerate "£8" style ints


def compute_annual(hourly: float) -> int:
    """Annual full-time equivalent, rounded to the nearest £10."""
    raw = hourly * FULL_TIME_HOURS_PER_WEEK * WEEKS_PER_YEAR
    return int(round(raw / 10) * 10)


def update_top_level_json_field(content: str, key: str, new_value) -> str:
    """
    Surgically replace a top-level JSON field, preserving all other formatting.
    Top-level fields are at 2-space indent in our file.
    """
    if isinstance(new_value, bool):
        raise ValueError("Boolean fields not supported")
    if isinstance(new_value, (int, float)):
        pattern = re.compile(rf'^(  "{re.escape(key)}":\s*)[\d.]+', re.MULTILINE)
        repl = rf"\g<1>{new_value}"
    else:
        encoded = json.dumps(str(new_value), ensure_ascii=False)
        pattern = re.compile(
            rf'^(  "{re.escape(key)}":\s*)"(?:[^"\\]|\\.)*"', re.MULTILINE
        )
        repl = rf"\g<1>{encoded}"
    new_content, n = pattern.subn(repl, content, count=1)
    if n == 0:
        raise RuntimeError(f"Could not find top-level field '{key}' in JSON")
    return new_content


def update_bundled_in_index(annual: int, hourly: float, updated_iso: str) -> bool:
    """
    Update the BUNDLED_DATA constants in index.html so that local-file users also
    see the latest NMW. Returns True if any change was made.
    """
    content = INDEX_FILE.read_text()
    original = content

    content = re.sub(
        r"(uk_nmw_annual:\s*)\d+",
        rf"\g<1>{annual}",
        content,
        count=1,
    )
    short_basis = (
        f"£{hourly:.2f}/hour × {FULL_TIME_HOURS_PER_WEEK}h/week × "
        f"{WEEKS_PER_YEAR} weeks (auto-refreshed {updated_iso})"
    )
    content = re.sub(
        r"(uk_nmw_basis:\s*)'[^']*'",
        lambda m: m.group(1) + repr(short_basis).replace('"', "'"),
        content,
        count=1,
    )
    content = re.sub(
        r"(updated:\s*)'[^']*'",
        rf"\g<1>'{updated_iso}'",
        content,
        count=1,
    )

    if content != original:
        INDEX_FILE.write_text(content)
        return True
    return False


def main() -> int:
    print(f"Fetching {NMW_PAGE_URL} ...")
    html = fetch(NMW_PAGE_URL)
    hourly = extract_nlw_rate(html)
    annual = compute_annual(hourly)
    print(
        f"Found NLW: £{hourly:.2f}/hour → "
        f"£{annual:,}/year ({FULL_TIME_HOURS_PER_WEEK}h × {WEEKS_PER_YEAR}wk)"
    )

    content = DATA_FILE.read_text()
    data = json.loads(content)
    current_annual = data.get("uk_nmw_annual")

    if current_annual == annual:
        print(f"No change (already £{annual:,}). Done.")
        return 0

    today = date.today().isoformat()
    print(f"Updating uk_nmw_annual: £{current_annual:,} → £{annual:,}")

    new_basis = (
        f"£{hourly:.2f}/hour × {FULL_TIME_HOURS_PER_WEEK}h/week × "
        f"{WEEKS_PER_YEAR} weeks. Auto-refreshed from gov.uk on {today}."
    )

    content = update_top_level_json_field(content, "uk_nmw_annual", annual)
    content = update_top_level_json_field(content, "uk_nmw_basis", new_basis)
    content = update_top_level_json_field(content, "updated", today)
    DATA_FILE.write_text(content)
    print(f"  wrote {DATA_FILE.relative_to(REPO_ROOT)}")

    if update_bundled_in_index(annual, hourly, today):
        print(f"  wrote {INDEX_FILE.relative_to(REPO_ROOT)} (bundled fallback)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
