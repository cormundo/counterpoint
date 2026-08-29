"""
Counterpoint framing/tone analysis: a separate pass over an existing
results/*.json file that describes *how* the five raw responses differ
in facts, framing/emphasis, and confidence/hedging - without ranking or
scoring any of them. This covers comparison dimensions 1-3 from
PROJECT_CONTEXT.md ("what each system knows", "how it frames the
event", "how willing it is to take a position").

This never edits or replaces the raw provider responses recorded by
query_models.py - it reads them and adds a separate "framing_analysis"
block to the same results file, clearly attributed to whichever model
produced it, so it's obvious this is a derived/synthesized layer and
not itself one of the five compared providers.

Known open tension: using one of the five providers to describe the
other four's framing raises the same "who judges the judge" concern
the project exists to avoid. Anthropic was picked here only because
it's the provider actually verified working end to end - not a claim
that it's a neutral referee. Worth discussing with Corey if this
becomes a permanent choice rather than a v1 placeholder.

Usage:
    python analyze_framing.py results/2026-08-29_example.json
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "config" / "models.yaml", encoding="utf-8") as f:
    MODEL_CONFIG = yaml.safe_load(f)["providers"]

ANALYZER_PROVIDER = "anthropic"

ANALYSIS_INSTRUCTIONS = """You are comparing five AI-generated responses to the identical prompt below. Your job is strictly descriptive: identify concrete, checkable DIFFERENCES between the responses. You must NOT rank, score, grade, or say any response is better, more accurate, more complete, or more trustworthy than another. Do not pick a "best" answer. Do not use words like "best", "worst", "better", "superior", "correct answer". Treat every response as equally worth describing.

Address exactly three things, each as a plain-prose paragraph (2-5 sentences), based only on what's actually different across the responses provided:

1. knowledge_differences: What facts, figures, names, or details appear in some responses but not others? Where do responses report different numbers or details for the same fact (e.g. different casualty counts)? Note the discrepancy - don't say which is right.
2. framing_differences: What does each response foreground vs. leave out or de-emphasize? Are there differences in word choice, tone, or what's presented as the central story?
3. confidence_differences: Where do responses hedge, express uncertainty, or caveat, versus stating things directly and confidently?

If the responses are largely similar on a dimension, say so plainly rather than inventing a difference.

Respond with ONLY a JSON object with exactly these three string keys: knowledge_differences, framing_differences, confidence_differences. No other text, no markdown code fence. Since this must be valid JSON: if you quote a word or phrase from one of the responses, use single quotes ('like this') rather than double quotes around it - a literal double-quote character inside a JSON string breaks parsing.

PROMPT GIVEN TO ALL FIVE MODELS:
{prompt_text}

RESPONSES:
{responses_block}
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_responses_block(results):
    parts = []
    for r in results:
        if r["status"] != "ok":
            continue
        parts.append(f"--- {r['provider']} ---\n{r['response']}\n")
    return "\n".join(parts)


def parse_json_response(text: str) -> dict:
    text = text.strip()
    # Models sometimes wrap JSON in a code fence despite instructions -
    # strip that defensively rather than failing the whole pass.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def analyze(results_file: Path):
    with open(results_file, encoding="utf-8") as f:
        data = json.load(f)

    ok_results = [r for r in data["results"] if r["status"] == "ok"]
    if len(ok_results) < 2:
        print("Fewer than 2 successful responses - nothing meaningful to compare, skipping analysis.")
        return data

    cfg = MODEL_CONFIG[ANALYZER_PROVIDER]
    prompt = ANALYSIS_INSTRUCTIONS.format(
        prompt_text=data["prompt_text"],
        responses_block=build_responses_block(data["results"]),
    )

    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # The model occasionally emits a stray character that breaks strict
    # JSON parsing despite the instructions - it's a formatting slip, not
    # a content problem, and a re-ask reliably produces valid JSON. Retry
    # a couple of times before giving up on what's usually a good analysis.
    analysis = None
    last_error = None
    for attempt in range(3):
        resp = client.messages.create(
            model=cfg["model"],
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        try:
            analysis = parse_json_response(text)
            break
        except json.JSONDecodeError as e:
            last_error = e
            print(f"Attempt {attempt + 1}: could not parse analysis JSON ({e}), retrying...")

    if analysis is None:
        print(f"Could not parse analysis JSON after 3 attempts: {last_error}\nRaw output:\n{text}")
        return data

    data["framing_analysis"] = {
        "analyzer_provider": ANALYZER_PROVIDER,
        "analyzer_model": cfg["model"],
        "generated_at": now_iso(),
        "knowledge_differences": analysis.get("knowledge_differences", ""),
        "framing_differences": analysis.get("framing_differences", ""),
        "confidence_differences": analysis.get("confidence_differences", ""),
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Added framing analysis to {results_file}")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file", type=Path)
    args = parser.parse_args()
    analyze(args.results_file)
