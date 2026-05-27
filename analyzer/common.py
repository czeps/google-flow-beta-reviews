"""Shared helpers for the feature-analysis pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
TAXONOMY_PATH = OUT_DIR / "features_taxonomy.json"
REVIEW_FEATURES_PATH = OUT_DIR / "review_features.csv"
FEATURES_CSV = OUT_DIR / "features.csv"
FEATURES_JSON = OUT_DIR / "features.json"

# Defaults; overridable via env or CLI.
MODEL_DEFAULT = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"


def client() -> Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env "
            "(copy .env.example) -- get a key at https://console.anthropic.com/settings/keys"
        )
    return Anthropic(api_key=key)


def resolve_model(name: str | None) -> str:
    if not name or name == "sonnet":
        return MODEL_DEFAULT
    if name == "haiku":
        return MODEL_HAIKU
    return name
