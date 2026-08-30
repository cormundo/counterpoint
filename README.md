# Counterpoint

Send one identical, editor-written prompt about a current event to five
frontier AI models — **OpenAI, Anthropic, Google, xAI, DeepSeek** — and
publish all five answers side by side, with **no ranking, no score, no
"winner."** The point isn't to find the best answer; it's to make the
*range* of plausible AI framings visible, since a single chatbot
screenshot never shows that a different model would have answered
differently.

Built for **[Consense](https://consenseai.org)** ("AI Against
Autocracy"). **→ Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) first**
— it explains *why* this tool works the way it does, and has the full
roadmap discussion. This file is just the "how to run it" reference.

**Live site:** https://cormundo.github.io/counterpoint/

---

## Status (as of 2026-08-29)

- **All five providers verified working end-to-end** with real API
  keys — search-triggered freshness, model IDs, and response quality
  all confirmed on live runs.
- **Three published comparisons:** a Nepal glacial flood, a Turkish
  band manager's arrest, and a Lake Ontario renaming dispute — the
  last one is a good demo of *why this tool matters*: DeepSeek flatly
  denies the event happened ("a dead internet meme") while the other
  four treat it as real and ongoing.
- **v1 framing/tone analysis** is live: a separate, clearly-labeled
  pass that *describes* how the five responses diverge (facts, framing,
  hedging) without ranking any of them.
- Repo is public with GitHub Pages auto-serving `docs/`.

See `PROJECT_CONTEXT.md` §3 for the full verification detail and known
rough edges, and §4 for what's next.

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in whichever provider keys you have in `.env` — a comparison
still runs with just one key (others show as `skipped_no_key`), so add
keys as you get them rather than waiting for all five.

Then, for any prompt file in `prompts/`:

```bash
python query_models.py prompts/<your-prompt>.yaml      # query all 5 providers
python analyze_framing.py results/<your-prompt>.json   # optional: how they differ
python render_results.py results/<your-prompt>.json    # build the HTML page
```

Open `docs/<your-prompt>.html`, or `docs/index.html` for the full list.
Commit + push to publish to the live site.

**Or skip hand-writing a prompt file** — run the local story feed
instead:

```bash
python feed_tool.py
```

Open http://127.0.0.1:5050. Browse real headlines (left) next to
comparisons already generated (right) for free; clicking a headline
shows a free, template-generated prompt; only clicking **Generate
comparison** runs the pipeline above and spends real API credit — with
a confirmation prompt first. This is **local-only, not on the public
site** — see "Why the feed is local-only" below.

---

## What's here

| Path | Purpose |
|---|---|
| `prompts/*.yaml` | One editor-written prompt per file (`YYYY-MM-DD_slug.yaml`). This *is* the versioning — every comparison traces to one git-tracked file. |
| `config/models.yaml` | Model IDs + freshness metadata per provider. Edit this, not the Python, when a provider ships a new model. |
| `config/feeds.yaml` | RSS sources for `feed_tool.py`. Add/remove outlets freely. |
| `query_models.py` | Queries all five providers, writes `results/<id>.json`. Handles missing keys, retries, and search-tool fallback gracefully. |
| `analyze_framing.py` | *Optional* second pass — adds a non-ranking `framing_analysis` block describing how responses diverge. |
| `render_results.py` + `templates/result.html` | Renders a results JSON into the styled comparison page in `docs/`. |
| `feed_tool.py` + `templates/feed.html` | Local-only tool: browse an RSS feed, turn a headline into a comparison in two clicks. |
| `results/*.json` | The reproducible record — one file per run. |
| `docs/` | Generated static site (named `docs/`, not `site/`, so GitHub Pages can serve it directly). |

### Why the feed is local-only

GitHub Pages is static hosting — it can't run Python or call paid APIs
when a visitor clicks something. A public "click to spend money"
button with no rate limiting would be a real cost/abuse risk for a
volunteer-funded nonprofit. So `feed_tool.py` is a small Flask app you
run on your own machine, using your own `.env` keys; it writes into
the same `prompts/`/`results/`/`docs/` files the rest of the pipeline
already uses. Review what it generated, then commit + push the ones
you want published, same as any other comparison.

The public site still shows the feed, so your team can see what it
looks like — `docs/feed.html` is a **static snapshot**: real headlines
frozen at generation time, the prompt preview still works (it's just
text, no server needed), but "Generate comparison" is disabled with a
note pointing at running it locally. Refresh that snapshot with:

```bash
python feed_tool.py --build-static
```

then commit + push `docs/feed.html` like anything else. It won't
update itself — re-run this whenever you want the public preview to
show newer headlines.

---

## Design notes

The visual design is checked against **the real consenseai.org HTML**
(not guessed): plain Tailwind CSS, default grayscale palette — no dark
navy/teal, no custom brand color — plus an italic "Impact"/Arial Black
wordmark. Two things worth preserving if you extend the layout:

- **The "spine"** (the connector line from the prompt into all five
  columns) is deliberate — equal weight into every column, matching
  the no-ranking principle.
- **The freshness badges** (`live search: yes/no/unknown`, `cutoff:
  ...`) are styled *identically regardless of value* — same gray pill,
  only the text changes — so they can never read as a quality signal.

---

## Known rough edges

- **Prompt re-runs overwrite history.** Running `query_models.py`
  twice on the same prompt file overwrites `results/<id>.json` — there
  is no run-history/versioning yet for a story that gets re-checked
  over time. Worth fixing before this becomes a real archive; see
  `PROJECT_CONTEXT.md` §4.
- **No automated tests.** Nothing catches a provider SDK's shape
  changing except a real run failing.
- Full list of gaps, priorities, and the open design questions (feed
  automation, cost, which models to add next) is in
  `PROJECT_CONTEXT.md` §4 — that's the living roadmap, this file isn't.

Once Claude Code is installed, `cd` into this directory and run
`claude`. A reasonable first prompt:

> Read `PROJECT_CONTEXT.md` first, then this README. Start with §4's
> priority list.
