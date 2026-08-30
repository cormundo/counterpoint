"""
Render a results/*.json file (produced by query_models.py) into a
static HTML side-by-side comparison page.

Usage:
    python render_results.py results/2026-08-29_example.json
"""

import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
SITE_DIR = BASE_DIR / "docs"
SITE_DIR.mkdir(exist_ok=True)


def render(results_file: Path) -> Path:
    with open(results_file, encoding="utf-8") as f:
        data = json.load(f)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("result.html")

    html = template.render(
        prompt_id=data["prompt_id"],
        prompt_text=data["prompt_text"],
        editor=data.get("editor"),
        run_started_at=data["run_started_at"],
        results=data["results"],
        num_columns=len(data["results"]),
        framing_analysis=data.get("framing_analysis"),
    )

    out_path = SITE_DIR / f"{data['prompt_id']}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def build_index():
    """List all rendered pages in a simple index."""
    pages = sorted(SITE_DIR.glob("*.html"), reverse=True)
    pages = [p for p in pages if p.name not in ("index.html", "feed.html")]
    links = "\n".join(
        f'<li><a href="{p.name}" class="block bg-white border border-gray-400 rounded-lg '
        f'shadow p-4 hover:bg-gray-100 transition-colors text-gray-800 font-mono text-sm">'
        f'{p.stem}</a></li>'
        for p in pages
    )
    if not links:
        links = '<li class="text-gray-500 italic">No comparisons rendered yet.</li>'
    index_html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Counterpoint — all comparisons</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  .impact-italic {{ font-family: Impact, 'Arial Black', sans-serif; font-style: italic; letter-spacing: 0.02em; }}
</style>
</head>
<body class="bg-gray-200 font-sans text-gray-800">
<header class="bg-gray-800 text-white py-4">
  <div class="container mx-auto px-6 flex flex-wrap justify-between items-center gap-2">
    <div>
      <div class="text-2xl font-bold impact-italic">Counterpoint</div>
      <div class="text-xs text-gray-300">
        <a href="https://consenseai.org" class="hover:text-white">Consense — AI Against Autocracy</a>
      </div>
    </div>
    <a href="feed.html" class="text-xs font-mono uppercase tracking-widest text-gray-300 hover:text-white">story feed</a>
  </div>
</header>
<main class="container mx-auto px-6 py-10 max-w-3xl">
  <h2 class="text-lg font-semibold text-gray-800 mb-4">All comparisons</h2>
  <ul class="space-y-3">
{links}
  </ul>
</main>
<footer class="bg-gray-900 text-white text-xs font-mono py-6 mt-12">
  <div class="container mx-auto px-6">
    Prompts, model versions, and retrieval timestamps are published in full so results can be independently checked.
  </div>
</footer>
</body></html>"""
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file", type=Path)
    args = parser.parse_args()
    out = render(args.results_file)
    build_index()
    print(f"Wrote {out}")
    print(f"Wrote {SITE_DIR / 'index.html'}")
