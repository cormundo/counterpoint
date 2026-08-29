# Counterpoint — Project Context

This document exists because whoever (or whatever) picks up this repo
next won't have the background conversations that shaped it. Read this
before making architectural decisions — several choices here (no
ranking, published prompts, cross-provider framing) are load-bearing
for the organization's actual goals, not arbitrary technical
preferences.

---

## 1. The organization

**Consense** ("Consense: AI Against Autocracy") — https://consenseai.org

A California nonprofit (501c3 status pending nationally as of mid-2026)
building AI tools aimed at strengthening democracy and countering
authoritarianism. Development spend across the organization has been
under $10,000 to date — this is a small, lean operation, not a funded
lab. Build accordingly: prefer boring, cheap, maintainable choices over
elaborate infrastructure.

**Mission** (from consenseai.org/our-values.html): use AI and data
tools to help human rights defenders, journalists, and civil society
resist authoritarianism; keep all tools open source; ground everything
in truth-seeking based on empirical evidence, even when inconvenient.

**Existing products:**
- **ConSenseAI** — a multi-model bot running publicly on X
  (@ConSenseAI) for over a year, drawing on multiple LLMs to compose
  replies. This is the organization's track record for running
  multi-model systems in live, adversarial public conditions.
  Repo: https://github.com/Nhorning/ConSenseAI
- **Quoracle** — an open-source orchestration engine where decisions
  are made by consensus across models from different providers.
  Built by Scott Helvick. Repo: https://github.com/shelvick/quoracle

**Team (relevant names you may see referenced):**
- Ewan Oglethorpe — founder, also founded Data Friendly Space
- Scott Helvick — technical lead, built Quoracle
- Jonathan Brass — former humanitarian program manager
- Corey Dickinson — the person building this scaffold; GIS/humanitarian
  background, not primarily a software engineer, currently doing this
  as "vibe coding" with heavy AI assistance
- Neil Horning — runs the ConSenseAI bot day to day

**Values that should constrain technical decisions:**
- Open source — this should end up as a public repo
- Truth/transparency — favor showing raw, unedited output over
  processed/summarized output; never silently drop or alter model
  responses
- Anti-concentration-of-power — this shows up directly in Counterpoint's
  design: no single model's answer is presented as more authoritative
  than another's

---

## 2. What Counterpoint is, and why it's built this way

**The problem it responds to:** People increasingly use AI to settle
arguments, and screenshots of chatbot answers circulate as evidence in
disputes. What a screenshot doesn't show is that a different model,
given the same question, often answers differently — in emphasis, in
confidence, and sometimes in substance. Those differences trace back to
which company built the model, what data it was trained on, what
country's regulatory regime it operates under, and whether it can
search the live web.

**The mechanism:** Send an identical, editor-written prompt about a
current news event to five frontier systems — OpenAI, Google,
Anthropic, xAI, and DeepSeek — chosen specifically because they span
different companies, different training approaches, and different
national/regulatory contexts (DeepSeek in particular gives a
non-US-aligned data point). Publish the five responses side by side.

**The three original comparison dimensions** (from the org's own
framing, written for a fellowship application):
1. **What each system knows** — factual content, completeness
2. **How each frames the event** — emphasis, word choice, what's
   foregrounded vs. omitted
3. **How willing each is to take a position** — hedging vs. directness,
   confidence in stated claims

**A fourth dimension Corey has since added and wants built in: how
current/up-to-date each system's information is** — i.e., whether a
response reflects live knowledge of a fast-moving event or stale
training-data knowledge. This was explicitly *dropped* from the
original fellowship pitch as out of scope ("whether a model searched
the web doesn't help two people argue better") but Corey has decided it
should be part of this build. Treat this as the current spec, not the
older document — but the tension is worth knowing about if you're
deciding how much engineering effort to spend on it.

**The core rule: no ranking, no scoring, no "winner."** The tool
describes differences; it never adjudicates them. This is not a minor
style preference — it's the organization's actual theory of change:
the working hypothesis is that seeing the range of plausible framings
of a contested event makes it harder for someone to treat their own
framing as the only reasonable one, which is meant to reduce
polarization. A UI that ranks, scores, color-codes by "quality," or
otherwise implies one answer is better undermines the entire premise.
Keep every provider visually and structurally equal — same card size,
same position weighting, no medals/badges/highlighting one over
another.

**Reproducibility is a credibility mechanism, not decoration.**
Prompts, model versions, and retrieval timestamps are published in
full with every result specifically so outside parties can check the
work themselves and it can't be dismissed as one company's framing.
Don't build anything that would make a past run unreproducible (e.g.
overwriting prompt files, silently changing model IDs without a
record).

**Longer-term direction (not yet built, but the target):**
- A public web interface (this scaffold's `render_results.py` +
  templates is the first step toward that)
- An MCP endpoint, so other organizations can call the comparison
  directly from their own tools instead of rebuilding it

---

## 3. What exists in this repo right now

- `query_models.py` — queries all five providers with one prompt,
  writes a JSON result file with model/version/timestamp/response per
  provider, plus freshness fields (`search_used`, `search_capable`,
  `knowledge_cutoff`). Gracefully skips providers with no API key
  configured (`status: skipped_no_key`), retries transient failures
  (2 retries, exponential backoff) before logging `status: error`, and
  falls back to a plain completion if a provider's search-enabled call
  fails, rather than losing that provider's response entirely.
- `config/models.yaml` — model IDs and per-provider freshness metadata,
  pulled out of `query_models.py` so they're one edit away instead of
  buried in code. IDs were pulled from provider docs on 2026-08-29 —
  see the warning at the top of that file before trusting them for
  anything important.
- `prompts/*.yaml` — one prompt per file, named by date + slug. This
  is the versioning mechanism referenced above.
- `results/*.json` — one file per run, the reproducible record.
- `render_results.py` + `templates/result.html` — renders a results
  JSON file into a static HTML side-by-side comparison page, including
  the freshness badges per response and the framing analysis section
  (see below) when one is present.
- `analyze_framing.py` — a separate pass, run between `query_models.py`
  and `render_results.py`, that describes how the raw responses differ
  on facts/framing/hedging (comparison dimensions 1–3 below) without
  ranking them, and writes the result into the same results JSON as a
  `framing_analysis` block. It never edits the raw responses. Currently
  uses Anthropic as the analyzer model — see the "known open tension"
  note in that file's docstring about the fairness of using one of the
  five compared providers as the analyzer; this is a v1 choice made
  because Anthropic was the verified-working provider, not a
  considered decision that it should stay that way.

**Verification status (as of 2026-08-29):** OpenAI, Anthropic, and
Google have all been exercised against live API keys and work end to
end — including live web search triggering correctly on all three and
returning real, current answers about an event outside training data
(see `results/2026-08-29_example.json`), and the framing analysis pass
correctly described real divergences between them (different casualty
figures, different geographic emphasis, different hedging on the
event's scientific classification) without ranking any of them. xAI's
search-enabled code path is implemented from current provider docs but
has never been run against a real key. DeepSeek has no search
capability as of the docs checked on that date, and hasn't been
run against a real key either.

The visual design in `templates/result.html` and `site/index.html` was
checked against a **raw fetch of consenseai.org's actual HTML** on
2026-08-29 (not a guess this time). Contrary to the original dark
navy/teal guess, the real site runs on plain Tailwind CSS with the
default grayscale palette — `bg-gray-800`/`bg-gray-900` dark sections,
`bg-gray-200` body, no custom brand color anywhere — plus an italic
"Impact"/Arial Black wordmark treatment. Both templates now match that.
If the live site's design changes, re-check against it again rather
than assuming this still matches.

---

## 4. What to build next, roughly in priority order

Items 1–5 from the original plan are done as of 2026-08-29 (visual
design matched to the real site, recency/freshness tracking, model IDs
moved to `config/models.yaml`, retry handling, a v1 framing/tone
analysis layer) — see section 3 above for verification status on each.
Remaining:

1. **Get real API keys for xAI and DeepSeek and actually run them.**
   xAI's search-enabled code path is implemented from current provider
   docs but untested — could fall back to a plain completion (harmless)
   or log a `status: error` (also harmless) once a real key is in
   place. DeepSeek just needs a key, no search path to worry about.
2. **Revisit the framing-analysis design, not just its plumbing.**
   The v1 in `analyze_framing.py` works and stays descriptive rather
   than evaluative in testing, but two things are worth a deliberate
   decision rather than staying as v1 defaults: (a) it currently uses
   Anthropic to analyze all five responses including Anthropic's own —
   decide whether that's acceptable long-term or whether the analyzer
   should be a separate/rotating/non-competing model; (b) it's a single
   prompt asking for prose description — consider whether a more
   structured diff (e.g. per-fact comparison table) would serve readers
   better than paragraphs, without turning into a scored rubric.
3. **Deployment.** Currently local-only static HTML — git isn't even
   installed on the machine this was built on yet. Once git/GitHub are
   set up, a GitHub Pages deploy of `site/` is the natural next step
   toward the "public interface" goal.
4. **MCP endpoint.** Explicitly a longer-term goal per the
   organization's stated plans, not immediate — don't over-invest here
   until the core comparison and interface are solid.

## 5. Constraints to keep in mind throughout

- This is a volunteer/low-budget nonprofit project. Favor free/cheap
  infrastructure (static hosting, minimal API calls) over anything
  that scales expensively.
- Corey is doing this largely via AI-assisted ("vibe coding")
  development, not from a professional software engineering
  background. Prefer clear, well-commented code and explicit
  explanations of tradeoffs over terse or clever implementations.
- Eventually this should be open source and public — avoid embedding
  anything (API keys, internal notes, unpublished org info) that
  shouldn't end up in a public repo.
