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

| Path | Purpose |
|---|---|
| `query_models.py` | Queries all five providers, writes `results/<id>.json` with model/version/timestamp/response + freshness fields (`search_used`, `search_capable`, `knowledge_cutoff`) per provider. Skips missing keys gracefully, retries transient failures (2x, exponential backoff), and falls back to a plain completion if a provider's search-enabled call fails rather than losing that provider's response entirely. |
| `config/models.yaml` | Model IDs + freshness metadata, pulled out of the Python so they're one edit away. IDs were pulled from provider docs on 2026-08-29 — **re-verify before trusting for anything important**, see the warning at the top of that file. |
| `analyze_framing.py` | A separate pass (run between `query_models.py` and `render_results.py`) that describes how raw responses diverge on facts/framing/hedging **without ranking them**, and writes a `framing_analysis` block into the same results JSON. Never edits the raw responses. Retries automatically if the analyzer model returns malformed JSON. Currently uses **Anthropic** as the analyzer — see the "known open tension" note in that file's docstring about the fairness of using one of the five compared providers as the judge; a v1 choice, not a considered decision that it should stay that way. |
| `render_results.py` + `templates/result.html` | Renders results JSON into the styled comparison page, including freshness badges and the framing analysis section when present. |
| `prompts/*.yaml`, `results/*.json`, `docs/` | The versioning/record/output layers — see README's table for detail. |

**Verification status (as of 2026-08-29):** all five providers —
OpenAI, Anthropic, Google, xAI, DeepSeek — have been exercised against
live API keys and work end to end, across three published comparisons
(Nepal glacial flood, a Turkish band manager's arrest, a Lake
Ontario/"Lake America" renaming dispute). Live web search triggers
correctly on the four search-capable providers, and the framing
analysis pass has correctly described real divergences without ranking
any of them — including, on the Lake America story, **DeepSeek flatly
denying the event happened at all** ("a dead internet meme") while the
other four treated it as a real, ongoing executive order. That's a
genuinely useful signal this tool is designed to surface, not a bug.

The visual design in `templates/result.html` and `docs/index.html` was
checked against a **raw fetch of consenseai.org's actual HTML**, not
guessed: plain Tailwind CSS, default grayscale palette (no dark
navy/teal, no custom brand color), italic "Impact"/Arial Black
wordmark. If the live site's design changes, re-check against it again
rather than assuming this still matches.

Deployment: the repo is **public** at github.com/cormundo/counterpoint
with GitHub Pages serving `docs/` from `master`. Re-render and push to
update the live site.

---

## 4. What to build next

Done as of 2026-08-29: visual design matched to the real site,
recency/freshness tracking (all 5 providers verified), model IDs moved
to `config/models.yaml`, retry handling, a v1 framing/tone analysis
layer, and public deployment via GitHub Pages. See §3 for verification
detail. Everything below is genuinely open — roughly grouped by theme,
not strict priority, since several of these should be discussed as a
team rather than decided solo.

### 4.1 A real gap to fix soon: re-runs overwrite history

`results/<prompt_id>.json` gets **overwritten** every time you re-run
that prompt file — there's no history. For a one-off comparison that's
fine; for a story like the three currently published, which are all
*still unfolding* (casualty counts climbing, an executive order that
could be litigated, an arrest that could be resolved), you'd want to
re-run periodically and see how each model's answer changes over time.
Right now that history is silently lost. This directly contradicts the
project's own reproducibility principle in §2 ("don't build anything
that would make a past run unreproducible"). Fix is straightforward:
either suffix result filenames with a run timestamp, or store a list of
runs per `prompt_id` in one file. Worth doing before publishing more
comparisons of evolving stories.

### 4.2 Sourcing prompts from a news feed, not just hand-typing them

The ask: instead of Corey (or another editor) hand-writing every prompt,
pull candidate stories from an external feed — RSS, a news API, GDELT,
or a curated list of outlets spanning regions/languages — so the tool
can keep up with the news cycle instead of waiting on manual curation.

**The design tension worth being explicit about:** *which stories get
compared* is itself an editorial act, same as the framing-analysis
"who judges the judge" tension in §3. A feed that's fully automated —
auto-generate prompt wording from a headline, auto-publish — imports
whatever bias or gaps exist in that feed's source selection, and
removes the human accountability the `editor:` field currently
represents. It also opens a manipulation surface: a bad actor gaming a
trending-topics feed could seed adversarial prompts.

**Recommended shape, not yet built:** a `fetch_candidates.py` script
that pulls headlines from a diverse set of sources and writes them as
*draft* prompt files (e.g. to `prompts/_drafts/`) — never straight into
the published `prompts/` directory. A human still writes the final
prompt wording and claims editorial credit before a comparison runs.
This keeps the feed as a triage/discovery aid, not a replacement for
editorial judgment. Bias toward stories where framing plausibly
diverges (contested political events, authoritarian-adjacent stories,
cross-border disputes) rather than pure "trending" — that's closer to
the org's actual mission than a generic news firehose.

If this works well, the natural extension is a scheduled job (e.g. a
GitHub Actions cron) that re-runs approved/recurring prompts on a
cadence — but that needs the run-history fix above first, and a hard
spend cap (see 4.4) before it's safe to leave unattended.

### 4.3 Robustness

- **No automated tests exist.** Nothing catches a provider SDK's
  response shape changing except a real run failing partway. Cheap
  wins: unit tests for `parse_json_response`'s edge cases, for
  `config/models.yaml` loading, and a "smoke test" that checks each
  provider function's structure without spending real tokens.
- **Dependencies are pinned loosely** (`>=` everywhere in
  `requirements.txt`). A future major SDK release could silently break
  a provider function the way `google-generativeai` → `google-genai`
  already did once this build cycle. Consider pinning exact versions
  once the provider integrations stabilize.
- **A lightweight CI check** (GitHub Actions, no API keys needed) that
  just verifies the code imports cleanly and `config/models.yaml`
  parses would catch a broken commit before it reaches `master`.
- **Schema-drift error messages:** right now a provider SDK shape
  change just surfaces as a generic exception caught by the
  search-fallback or retry logic — functional, but the real cause gets
  buried. Worth adding a narrower except clause that specifically flags
  "provider response shape may have changed" so it's diagnosable at a
  glance instead of by reading a stack trace.

### 4.4 Cost

- **Provider batch APIs** (Anthropic's Batches API, OpenAI's Batch API)
  are typically ~50% cheaper than synchronous calls and fit this use
  case well — nobody's waiting live on a Counterpoint run the way a
  chat user waits on a reply. Worth adopting once runs happen often
  enough to matter.
- **Cap search tool usage on every provider, not just Anthropic.**
  Anthropic's `web_search` tool is already capped at `max_uses: 3`;
  OpenAI/Google/xAI's search tools aren't currently capped, which is a
  real (if probably small) runaway-cost exposure once this runs
  unattended.
- **A cheaper analyzer model for `analyze_framing.py`** is worth
  testing (e.g. Haiku 4.5 instead of Sonnet 5) — but treat it as a
  genuine tradeoff to evaluate, not a free win; a weaker model may
  produce shallower framing analysis, and that section's whole value is
  being accurate and specific.
- **A spend cap is a prerequisite for any automation** (4.2's
  scheduled runs, or just more frequent manual ones) — this is a
  volunteer nonprofit with under $10k in dev spend to date; automated
  or scheduled runs need a hard ceiling before they run unattended.

### 4.5 Other models worth adding

The org's own selection criteria (§2): different companies, different
training approaches, different national/regulatory contexts. Candidates
that would extend that range, not just add another US company:

- **Mistral (France/EU)** — the current five have no EU-regulated
  (AI Act) data point at all.
- **Alibaba Qwen (China)** — DeepSeek is currently the only Chinese
  lab represented, which risks flattening "Chinese AI" into one data
  point. That's in tension with the project's own anti-single-narrative
  premise.
- **Meta Llama (US, open-weight)** — a different distribution model
  from the other four US/China labs, and resonates with the org's own
  open-source commitment.
- **Cohere (Canada)** — another distinct jurisdiction, enterprise-
  focused.

Worth a real discussion before adding: more columns means more API
cost per run, a harder "equal visual weight" layout as columns grow
past five, and a longer/costlier framing-analysis prompt (it processes
all raw responses in one context). **Perplexity** came up as a
different-category option — it wraps other companies' models with
retrieval rather than training its own, so it doesn't cleanly fit "which
company built the model"; worth a separate conversation about whether
it belongs at all rather than folding it in by default.

### 4.6 Smaller things worth doing

- **No a11y pass yet** — this is meant to be a public credibility tool;
  worth a basic screen-reader/contrast check before wide release.
- **Everything's English-only so far.** The "different national/
  regulatory context" premise would be stronger with non-English
  prompts too, especially for stories where the framing gap is likely
  to track language/audience, not just company.
- **Revisit the framing-analysis design** (not just its plumbing): (a)
  Anthropic currently judges all five responses including its own —
  decide if that's acceptable long-term or if the analyzer should
  rotate/be non-competing; (b) it's single-prompt prose — a more
  structured per-fact diff might serve readers better than paragraphs,
  without turning into a scored rubric.
- **MCP endpoint** — still explicitly longer-term per the org's stated
  plans; don't over-invest until the core comparison/interface and the
  items above are solid.

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
