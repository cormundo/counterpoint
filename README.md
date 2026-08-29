# Counterpoint — starter scaffold

**Start with `PROJECT_CONTEXT.md`** for the organization background,
why this tool is built the way it is, and what to build next. This
README just covers running what exists.

Minimal working core: send one editor-written prompt to five frontier
models, record exact model version + retrieval timestamp for each, and
save the result as a single reproducible JSON file.

## What's here

- `prompts/` — one YAML file per prompt, named `YYYY-MM-DD_slug.yaml`.
  This is your versioning: every comparison run traces back to one
  file in git history.
- `config/models.yaml` — model IDs and freshness metadata for each
  provider. Edit this, not the Python, when a provider ships a new
  model.
- `query_models.py` — queries all five providers and writes
  `results/<prompt_id>.json`.
- `analyze_framing.py` — optional second pass that adds a
  `framing_analysis` block describing how the responses differ (facts,
  framing, hedging) without ranking them. Run after `query_models.py`.
- `results/` — output, one JSON file per run.
- `.env.example` — copy to `.env`, fill in your API keys.

## Running it

```
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in whichever provider keys you have —
`ANTHROPIC_API_KEY` at minimum. The script checks for each key before
calling that provider and marks it `skipped_no_key` in the output
instead of failing, so you can run the full pipeline with however many
providers you've got keys for and add the rest later. As of 2026-08-29,
OpenAI, Anthropic, and Google have all been verified working
end-to-end with real keys; xAI and DeepSeek still need keys added to
`.env` to test.

```
python query_models.py prompts/2026-08-29_example.yaml
python analyze_framing.py results/2026-08-29_example.json
python render_results.py results/2026-08-29_example.json
```

Check `results/2026-08-29_example.json` for the raw data, or open
`docs/2026-08-29_example.html` in a browser for the rendered
comparison (the analysis step is optional — skip it and
`render_results.py` just won't show the "How the responses differ"
section).

## Known gaps — this is a starting point, not the product

- **Recency/freshness tracking is wired in, but only proven against
  Anthropic.** `query_models.py` now tries to enable each provider's
  live web search tool and records `search_used` (true/false/unknown)
  and `knowledge_cutoff` per response. If the search-enabled call fails
  for any reason (wrong tool syntax for that SDK version, feature not
  enabled on the account, etc.) it silently falls back to a plain
  completion so one provider's search quirks can't take down the whole
  run — `search_used` just comes back `unknown` in that case. Only
  Anthropic has actually been exercised against a live key so far and
  it worked (confirmed live search triggering and a real, current
  answer). OpenAI/Google/xAI are implemented from current provider docs
  but **untested** — verify against a real key before trusting them.
- Model IDs and freshness settings now live in `config/models.yaml`
  instead of being hardcoded in `query_models.py`. The IDs there were
  pulled from provider docs on 2026-08-29 — re-verify before an
  important run, see the warning at the top of that file.
  `knowledge_cutoff` is intentionally left blank for every provider —
  it wasn't confirmed from documentation, and a blank field is more
  honest than a guessed date.
- Basic retry handling: transient failures get 2 retries with
  exponential backoff before being logged as `status: error`.
- **Framing/tone analysis layer — v1 exists.** `analyze_framing.py` is
  a separate pass (run after `query_models.py`, before
  `render_results.py`) that reads the raw responses already recorded
  and asks one model (currently Anthropic — see the "known open
  tension" note in that file's docstring about using one of the five
  compared providers as the analyzer) to describe, in plain prose,
  where the responses diverge on facts, framing/emphasis, and
  hedging/confidence. It's instructed never to rank or grade — verified
  in testing that it sticks to description (e.g. flagging that two
  responses cite different casualty counts, not which one is right).
  The result is stored as a `framing_analysis` block in the results
  JSON and rendered as its own clearly-labeled section below the raw
  response grid, never mixed into or replacing the raw cards.
- No public interface or MCP endpoint yet — this is just the engine.
- Provider SDK auth patterns vary and aren't validated against each
  provider's current docs — check credentials/model names against
  each provider's docs before relying on this.

## Interface (basic)

`render_results.py` turns a results JSON file into a static HTML
comparison page, styled to match the real consenseai.org site (see
design notes below). Output goes in `docs/` rather than `site/` so it
can be served directly by GitHub Pages.

```
pip install jinja2  # already in requirements.txt
python render_results.py results/2026-08-29_example.json
```

Open `docs/2026-08-29_example.html` in a browser. `docs/index.html`
lists every rendered comparison.

Design notes for whoever picks this up next:
- The visual design was checked against the live consenseai.org HTML
  (2026-08-29), not guessed. The real site runs on plain Tailwind CSS
  with the default grayscale palette (no dark navy/teal, no custom
  brand color) and an italic "Impact"/Arial Black wordmark treatment —
  `templates/result.html` and the generated `docs/index.html` match
  that: Tailwind via CDN, `bg-gray-800` header, `bg-gray-200` body,
  `bg-gray-900` footer, no accent color anywhere.
- The "spine" (the connecting line from the prompt into all five
  columns) is deliberate: equal length and weight into every column,
  no column emphasized, matching the "we don't rank" principle. Keep
  that if extending the layout.
- The freshness badges (`live search: yes/no/unknown`, `cutoff: ...`)
  are styled identically regardless of value — same gray pill, only the
  text changes — so they can't read as a quality judgment either.
- No pagination/search/filtering across many results yet — fine for a
  handful of runs, not for a real archive.

Once Claude Code is installed, `cd` into this directory and run `claude`.
A reasonable first prompt:

> Read PROJECT_CONTEXT.md first, then README.md, query_models.py,
> render_results.py, and templates/result.html. Start with the
> priority list in PROJECT_CONTEXT.md section 4 — begin with item 1
> (verify the visual design against the real consenseai.org site).
