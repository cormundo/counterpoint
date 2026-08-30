"""
Local-only story-browsing tool: shows an RSS feed of current headlines
next to the comparisons already generated, and lets you turn a
headline into a new Counterpoint comparison in two explicit clicks -
one to see the (free, template-generated) prompt, one to actually run
it against all five providers.

This is deliberately local-only, not part of the public GitHub Pages
site: generating a comparison spends real API money, and a public
"click to spend money" button with no rate limiting would be a real
cost/abuse risk for a volunteer-funded nonprofit. Run this yourself,
review what it generates, then commit + push the results you want
published - exactly the same results/prompts/docs files the rest of
the pipeline already produces.

Usage:
    python feed_tool.py
    (then open http://127.0.0.1:5050 in your browser)
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml
from flask import Flask, jsonify, request, send_from_directory
from jinja2 import Environment, FileSystemLoader

import analyze_framing
import query_models
import render_results

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
RESULTS_DIR = BASE_DIR / "results"
DOCS_DIR = BASE_DIR / "docs"
TEMPLATES_DIR = BASE_DIR / "templates"

with open(BASE_DIR / "config" / "feeds.yaml", encoding="utf-8") as f:
    FEEDS = yaml.safe_load(f)["feeds"]

app = Flask(__name__)
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60].rstrip("-")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def prompt_text_for(title: str) -> str:
    # Deliberately generic and template-only (no LLM call) - the point
    # is a prompt that costs nothing to produce for any headline, not
    # a tailored one. Matches the phrasing of the hand-written prompts
    # already in prompts/ for consistency.
    return f'Summarize what happened regarding "{title}" and explain the current state of the situation as of today.'


@app.route("/")
def index():
    return jinja_env.get_template("feed.html").render()


@app.route("/api/feed")
def api_feed():
    items = []
    seen_titles = set()
    for feed in FEEDS:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[:15]:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            prompt_id = f"{today()}_{slugify(title)}"
            items.append({
                "id": prompt_id,
                "title": title,
                "source": feed["name"],
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "prompt_text": prompt_text_for(title),
                "already_generated": (RESULTS_DIR / f"{prompt_id}.json").exists(),
            })
    return jsonify({"items": items})


@app.route("/api/comparisons")
def api_comparisons():
    pages = sorted(DOCS_DIR.glob("*.html"), reverse=True)
    return jsonify({"comparisons": [p.stem for p in pages if p.name != "index.html"]})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    prompt_id = data["id"]
    title = data["title"]
    prompt_text = data["prompt_text"]

    results_path = RESULTS_DIR / f"{prompt_id}.json"
    if results_path.exists():
        # Never silently re-spend on something already generated today -
        # see PROJECT_CONTEXT.md on the run-history gap this sidesteps.
        return jsonify({"status": "already_exists", "id": prompt_id})

    prompt_path = PROMPTS_DIR / f"{prompt_id}.yaml"
    if not prompt_path.exists():
        prompt_path.write_text(
            yaml.safe_dump(
                {
                    "id": prompt_id,
                    "editor": "corey",
                    "prompt": prompt_text,
                    "source_title": title,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    query_models.run(prompt_path)
    analyze_framing.analyze(results_path)
    render_results.render(results_path)
    render_results.build_index()

    return jsonify({"status": "ok", "id": prompt_id})


@app.route("/docs/<path:filename>")
def serve_docs(filename):
    return send_from_directory(DOCS_DIR, filename)


if __name__ == "__main__":
    print("Counterpoint story feed - open http://127.0.0.1:5050 in your browser")
    app.run(port=5050, debug=False)
