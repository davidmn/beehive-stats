#!/usr/bin/env python3
"""Generate a static HTML index of all league submissions."""

from __future__ import annotations

import csv
import html
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT_DIR / "exports"
OUTPUT_FILE = ROOT_DIR / "index.html"


def discover_submission_files(exports_dir: Path) -> list[Path]:
    """Return every submissions.csv file under exports/."""
    return sorted(exports_dir.glob("**/submissions.csv"))


def discover_round_files(exports_dir: Path) -> list[Path]:
    """Return every rounds.csv file under exports/."""
    return sorted(exports_dir.glob("**/rounds.csv"))


def discover_competitor_files(exports_dir: Path) -> list[Path]:
    """Return every competitors.csv file under exports/."""
    return sorted(exports_dir.glob("**/competitors.csv"))


def parse_league_from_path(path: Path, exports_dir: Path) -> str:
    """Infer league name from path: exports/<league>/submissions.csv."""
    relative = path.relative_to(exports_dir)
    if len(relative.parts) >= 2:
        return relative.parts[0]
    return "unknown"


def load_rows(submission_files: list[Path]) -> list[dict[str, str]]:
    """Load all CSV rows and include their league name."""
    rows: list[dict[str, str]] = []
    for csv_path in submission_files:
        league = parse_league_from_path(csv_path, EXPORTS_DIR)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                row["League"] = league
                rows.append(row)
    return rows


def load_rounds_map(round_files: list[Path]) -> dict[tuple[str, str], dict[str, str]]:
    """Map (league, round_id) to round metadata."""
    rounds_map: dict[tuple[str, str], dict[str, str]] = {}
    for csv_path in round_files:
        league = parse_league_from_path(csv_path, EXPORTS_DIR)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                round_id = (row.get("ID") or "").strip()
                if not round_id:
                    continue
                rounds_map[(league, round_id)] = row
    return rounds_map


def load_competitors_map(
    competitor_files: list[Path],
) -> dict[tuple[str, str], dict[str, str]]:
    """Map (league, competitor_id) to competitor metadata."""
    competitors_map: dict[tuple[str, str], dict[str, str]] = {}
    for csv_path in competitor_files:
        league = parse_league_from_path(csv_path, EXPORTS_DIR)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                competitor_id = (row.get("ID") or "").strip()
                if not competitor_id:
                    continue
                competitors_map[(league, competitor_id)] = row
    return competitors_map


def enrich_submission_rows(
    rows: list[dict[str, str]],
    rounds_map: dict[tuple[str, str], dict[str, str]],
    competitors_map: dict[tuple[str, str], dict[str, str]],
) -> None:
    """Attach round details to each submission row in-place."""
    for row in rows:
        league = row.get("League", "")
        round_id = row.get("Round ID", "")
        submitter_id = row.get("Submitter ID", "")
        round_row = rounds_map.get((league, round_id), {})
        competitor_row = competitors_map.get((league, submitter_id), {})
        row["Round Name"] = round_row.get("Name", "")
        row["Round Description"] = round_row.get("Description", "")
        row["Round Playlist URL"] = round_row.get("Playlist URL", "")
        row["Submitter Name"] = competitor_row.get("Name", "")


def format_cell(value: str) -> str:
    return html.escape(value or "")


def spotify_link(uri: str) -> str:
    if uri.startswith("spotify:track:"):
        track_id = uri.split(":")[-1]
        return f"https://open.spotify.com/track/{track_id}"
    return ""


def render_html(rows: list[dict[str, str]], league_count: int) -> str:
    """Render a complete static HTML page."""
    table_rows: list[str] = []
    for row in rows:
        uri = row.get("Spotify URI", "")
        link = spotify_link(uri)
        uri_cell = (
            f'<a href="{format_cell(link)}" target="_blank" rel="noopener noreferrer">Open</a>'
            if link
            else format_cell(uri)
        )
        table_rows.append(
            "<tr>"
            f"<td>{format_cell(row.get('Title', ''))}</td>"
            f"<td>{format_cell(row.get('Artist(s)', ''))}</td>"
            f"<td>{format_cell(row.get('Album', ''))}</td>"
            f"<td>{format_cell(row.get('Round Name', ''))}</td>"
            f"<td>{format_cell(row.get('Submitter Name', ''))}</td>"
            f"<td>{uri_cell}</td>"
            "</tr>"
        )

    rows_html = "\n".join(table_rows)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Beehive Sats Submissions</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    body {{
      margin: 0;
      padding: 1.5rem;
      line-height: 1.4;
    }}
    h1, p {{
      margin: 0 0 0.75rem 0;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid #8884;
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 900px;
    }}
    thead {{
      position: sticky;
      top: 0;
      background: #8883;
      backdrop-filter: blur(4px);
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid #8883;
      padding: 0.5rem;
      vertical-align: top;
    }}
    tbody tr:hover {{
      background: #8882;
    }}
  </style>
</head>
<body>
  <h1>All Submitted Tracks</h1>
  <p>{len(rows)} tracks across {league_count} league(s).</p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Artist(s)</th>
          <th>Album</th>
          <th>Round</th>
          <th>Submitter</th>
          <th>Spotify</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> int:
    submission_files = discover_submission_files(EXPORTS_DIR)
    round_files = discover_round_files(EXPORTS_DIR)
    competitor_files = discover_competitor_files(EXPORTS_DIR)
    rounds_map = load_rounds_map(round_files)
    competitors_map = load_competitors_map(competitor_files)
    rows = load_rows(submission_files)
    enrich_submission_rows(rows, rounds_map, competitors_map)
    rows.sort(key=lambda row: row.get("Created", ""))

    html_output = render_html(rows, league_count=len({row["League"] for row in rows}))
    OUTPUT_FILE.write_text(html_output, encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
