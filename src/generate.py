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


def discover_vote_files(exports_dir: Path) -> list[Path]:
    """Return every votes.csv file under exports/."""
    return sorted(exports_dir.glob("**/votes.csv"))


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


def load_points_map(vote_files: list[Path]) -> dict[tuple[str, str, str], int]:
    """Map (league, round_id, spotify_uri) to total points."""
    points_map: dict[tuple[str, str, str], int] = {}
    for csv_path in vote_files:
        league = parse_league_from_path(csv_path, EXPORTS_DIR)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                round_id = (row.get("Round ID") or "").strip()
                spotify_uri = (row.get("Spotify URI") or "").strip()
                points_raw = (row.get("Points Assigned") or "").strip()
                if not round_id or not spotify_uri:
                    continue
                try:
                    points = int(points_raw)
                except ValueError:
                    points = 0
                key = (league, round_id, spotify_uri)
                points_map[key] = points_map.get(key, 0) + points
    return points_map


def enrich_submission_rows(
    rows: list[dict[str, str]],
    rounds_map: dict[tuple[str, str], dict[str, str]],
    competitors_map: dict[tuple[str, str], dict[str, str]],
    points_map: dict[tuple[str, str, str], int],
) -> None:
    """Attach round details to each submission row in-place."""
    for row in rows:
        league = row.get("League", "")
        round_id = row.get("Round ID", "")
        submitter_id = row.get("Submitter ID", "")
        spotify_uri = row.get("Spotify URI", "")
        round_row = rounds_map.get((league, round_id), {})
        competitor_row = competitors_map.get((league, submitter_id), {})
        points = points_map.get((league, round_id, spotify_uri), 0)
        row["Round Name"] = round_row.get("Name", "")
        row["Round Description"] = round_row.get("Description", "")
        row["Round Playlist URL"] = round_row.get("Playlist URL", "")
        row["Submitter Name"] = competitor_row.get("Name", "")
        row["Points"] = str(points)


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
            f'<td data-sort="{format_cell(row.get("Points", "0"))}">{format_cell(row.get("Points", "0"))}</td>'
            f'<td data-sort="{format_cell(uri)}">{uri_cell}</td>'
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
    th button {{
      all: unset;
      cursor: pointer;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }}
    th button::after {{
      content: "↕";
      font-size: 0.8em;
      opacity: 0.65;
    }}
    th button[data-dir="asc"]::after {{
      content: "↑";
      opacity: 1;
    }}
    th button[data-dir="desc"]::after {{
      content: "↓";
      opacity: 1;
    }}
    tbody tr:hover {{
      background: #8882;
    }}
    footer {{
      margin-top: 1rem;
      font-size: 0.95rem;
      opacity: 0.9;
    }}
    footer a {{
      color: inherit;
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
          <th><button type="button">Title</button></th>
          <th><button type="button">Artist(s)</button></th>
          <th><button type="button">Album</button></th>
          <th><button type="button">Round</button></th>
          <th><button type="button">Submitter</button></th>
          <th><button type="button">Points</button></th>
          <th><button type="button">Spotify</button></th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
  <footer>
    Made by <a href="https://bsky.app/profile/megaslippers.net" target="_blank" rel="noopener noreferrer">MegaSlippers</a> -
    <a href="https://github.com/davidmn/beehive-stats" target="_blank" rel="noopener noreferrer">Repo</a>
  </footer>
  <script>
    (() => {{
      const table = document.querySelector("table");
      const tbody = table?.querySelector("tbody");
      const headerButtons = table?.querySelectorAll("thead th button");
      if (!table || !tbody || !headerButtons) return;

      let sortedColumn = -1;
      let sortDirection = "asc";

      const getCellSortValue = (row, columnIndex) => {{
        const cell = row.cells[columnIndex];
        if (!cell) return "";
        const customSort = cell.dataset.sort;
        if (customSort !== undefined) return customSort.toLowerCase();
        return (cell.textContent || "").trim().toLowerCase();
      }};

      const updateIndicators = () => {{
        headerButtons.forEach((button, index) => {{
          if (index === sortedColumn) {{
            button.dataset.dir = sortDirection;
          }} else {{
            delete button.dataset.dir;
          }}
        }});
      }};

      headerButtons.forEach((button, columnIndex) => {{
        button.addEventListener("click", () => {{
          const rows = Array.from(tbody.querySelectorAll("tr"));
          if (rows.length === 0) return;

          if (sortedColumn === columnIndex) {{
            sortDirection = sortDirection === "asc" ? "desc" : "asc";
          }} else {{
            sortedColumn = columnIndex;
            sortDirection = "asc";
          }}

          rows.sort((a, b) => {{
            const aValue = getCellSortValue(a, columnIndex);
            const bValue = getCellSortValue(b, columnIndex);
            const compare = aValue.localeCompare(bValue, undefined, {{
              numeric: true,
              sensitivity: "base",
            }});
            return sortDirection === "asc" ? compare : -compare;
          }});

          const fragment = document.createDocumentFragment();
          rows.forEach((row) => fragment.appendChild(row));
          tbody.appendChild(fragment);
          updateIndicators();
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


def main() -> int:
    submission_files = discover_submission_files(EXPORTS_DIR)
    round_files = discover_round_files(EXPORTS_DIR)
    competitor_files = discover_competitor_files(EXPORTS_DIR)
    vote_files = discover_vote_files(EXPORTS_DIR)
    rounds_map = load_rounds_map(round_files)
    competitors_map = load_competitors_map(competitor_files)
    points_map = load_points_map(vote_files)
    rows = load_rows(submission_files)
    enrich_submission_rows(rows, rounds_map, competitors_map, points_map)
    rows.sort(key=lambda row: row.get("Created", ""))

    html_output = render_html(rows, league_count=len({row["League"] for row in rows}))
    OUTPUT_FILE.write_text(html_output, encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
