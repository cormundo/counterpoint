"""
Counterpoint core: send one editor-written prompt to five frontier models
and log the responses side by side with model version, timestamp, and
freshness info (did the model use live web search, or answer from
training data alone).

Usage:
    python query_models.py prompts/2026-08-29_example.yaml
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

with open(BASE_DIR / "config" / "models.yaml", encoding="utf-8") as f:
    MODEL_CONFIG = yaml.safe_load(f)["providers"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def call_with_retry(fn, *args, retries=2, base_delay=2.0, **kwargs):
    """Retry a provider call on transient failures (rate limits, network
    blips) with exponential backoff. Doesn't hide a genuinely broken
    integration — it just gives transient errors a couple of chances
    before we log the failure and move on."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < retries:
                wait = base_delay * (2 ** attempt)
                print(f"  retrying after error ({e}); waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
    raise last_exc


def query_openai(prompt: str, model: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    search_used = None
    try:
        # Responses API with the web_search tool enabled, so the model can
        # answer from live web content instead of training data alone.
        resp = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        search_used = any(item.type == "web_search_call" for item in resp.output)
        text = resp.output_text
    except Exception:
        # Search-enabled call failed (wrong tool syntax for this SDK
        # version, feature not enabled for this account, etc.) - fall
        # back to a plain completion rather than losing the whole
        # provider over a recency-tracking feature.
        search_used = None
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content

    return {
        "provider": "openai",
        "model": model,
        "response": text,
        "search_used": search_used,
        "retrieved_at": now_iso(),
    }


def query_anthropic(prompt: str, model: str) -> dict:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    search_used = None
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        )
        search_used = any(block.type == "server_tool_use" for block in resp.content)
        text = "".join(block.text for block in resp.content if block.type == "text")
    except Exception:
        search_used = None
        resp = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text

    return {
        "provider": "anthropic",
        "model": model,
        "response": text,
        "search_used": search_used,
        "retrieved_at": now_iso(),
    }


def query_google(prompt: str, model: str) -> dict:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    search_used = None
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        candidate = resp.candidates[0]
        search_used = bool(getattr(candidate, "grounding_metadata", None))
        text = resp.text
    except Exception:
        search_used = None
        resp = client.models.generate_content(model=model, contents=prompt)
        text = resp.text

    return {
        "provider": "google",
        "model": model,
        "response": text,
        "search_used": search_used,
        "retrieved_at": now_iso(),
    }


def query_xai(prompt: str, model: str) -> dict:
    # xAI's API is OpenAI-compatible.
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

    search_used = None
    try:
        resp = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        search_used = bool(getattr(resp, "server_side_tool_usage", None))
        text = resp.output_text
    except Exception:
        search_used = None
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content

    return {
        "provider": "xai",
        "model": model,
        "response": text,
        "search_used": search_used,
        "retrieved_at": now_iso(),
    }


def query_deepseek(prompt: str, model: str) -> dict:
    # DeepSeek's API is OpenAI-compatible. No live search tool as of the
    # docs checked 2026-08-29 - every response is training-data only.
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "provider": "deepseek",
        "model": model,
        "response": resp.choices[0].message.content,
        "search_used": False,
        "retrieved_at": now_iso(),
    }


PROVIDERS = {
    "openai": query_openai,
    "anthropic": query_anthropic,
    "google": query_google,
    "xai": query_xai,
    "deepseek": query_deepseek,
}


REQUIRED_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def run(prompt_file: Path):
    with open(prompt_file, encoding="utf-8") as f:
        prompt_data = yaml.safe_load(f)

    prompt_text = prompt_data["prompt"].strip()
    prompt_id = prompt_data["id"]

    results = []
    for name, fn in PROVIDERS.items():
        cfg = MODEL_CONFIG[name]
        key_name = REQUIRED_KEYS[name]
        if not os.environ.get(key_name):
            print(f"Skipping {name} (no {key_name} set)")
            results.append({
                "provider": name,
                "model": None,
                "response": None,
                "status": "skipped_no_key",
                "search_used": None,
                "search_capable": cfg["supports_search"],
                "knowledge_cutoff": cfg["knowledge_cutoff"],
                "retrieved_at": now_iso(),
            })
            continue
        try:
            print(f"Querying {name}...")
            result = call_with_retry(fn, prompt_text, cfg["model"])
            result["status"] = "ok"
            result["search_capable"] = cfg["supports_search"]
            result["knowledge_cutoff"] = cfg["knowledge_cutoff"]
            results.append(result)
        except Exception as e:
            print(f"  {name} failed: {e}", file=sys.stderr)
            results.append({
                "provider": name,
                "model": cfg["model"],
                "response": None,
                "status": "error",
                "error": str(e),
                "search_used": None,
                "search_capable": cfg["supports_search"],
                "knowledge_cutoff": cfg["knowledge_cutoff"],
                "retrieved_at": now_iso(),
            })

    run_record = {
        "prompt_id": prompt_id,
        "prompt_text": prompt_text,
        "editor": prompt_data.get("editor"),
        "run_started_at": results[0]["retrieved_at"] if results else now_iso(),
        "results": results,
    }

    out_path = RESULTS_DIR / f"{prompt_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(run_record, f, indent=2, ensure_ascii=False)

    print(f"\nSaved results to {out_path}")
    return run_record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt_file", type=Path)
    args = parser.parse_args()
    run(args.prompt_file)
