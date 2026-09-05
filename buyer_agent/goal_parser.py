from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

CATEGORIES = {
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "runner", "trainers", "footwear", "boot", "boots", "oxford"],
    "socks": ["sock", "socks"],
    "shoe-care": ["care", "cleaner", "polish", "spray", "cream", "kit"],
    "insoles": ["insole", "insoles", "arch"],
    "laces": ["lace", "laces"],
    "bags": ["bag", "duffel", "duffle"],
}

ATTRIBUTE_WORDS = {
    "breathable": ["breathable", "mesh", "ventilated", "airy"],
    "waterproof": ["waterproof", "water-resistant", "rain"],
}


class ParsedGoal(BaseModel):
    category: str | None = None
    max_price_inr: float | None = Field(default=None, gt=0)
    keywords: list[str] = Field(default_factory=list)
    must_have_attributes: list[str] = Field(default_factory=list)
    quantity: int = Field(default=1, ge=1, le=5)
    notes: str = ""

    @field_validator("keywords", "must_have_attributes")
    @classmethod
    def lower_list(cls, values: list[str]) -> list[str]:
        return [item.strip().lower() for item in values if item and item.strip()]

    @field_validator("category")
    @classmethod
    def lower_category(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None


def parse_goal(text: str, force_fallback: bool = False) -> tuple[ParsedGoal, str]:
    """Return (goal, parser_used). LLM output is schema-validated; never trusted raw."""
    if not force_fallback and ANTHROPIC_API_KEY:
        try:
            return _parse_with_llm(text), "claude"
        except Exception:
            fallback = _parse_deterministic(text)
            return fallback, "deterministic_fallback_after_llm_error"
    return _parse_deterministic(text), "deterministic"


def _parse_with_llm(text: str) -> ParsedGoal:
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=400,
        system=(
            "Extract shopping filters as JSON only. No markdown. "
            "Schema: {category: string|null, max_price_inr: number|null, "
            "keywords: string[], must_have_attributes: string[], quantity: int, notes: string}. "
            "category must be one of: shoes, socks, shoe-care, insoles, laces, bags, or null. "
            "must_have_attributes may include breathable or waterproof when the user asks."
        ),
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in message.content if getattr(block, "text", None))
    data = _extract_json(raw)
    return ParsedGoal.model_validate(data)


def _extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).removesuffix("```").strip()
    return json.loads(raw)


def _parse_deterministic(text: str) -> ParsedGoal:
    lowered = text.lower()
    category = None
    for name, aliases in CATEGORIES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases):
            category = name
            break
    if category is None and any(word in lowered for word in ["run", "running", "trail", "hike"]):
        category = "shoes"

    max_price = None
    price_match = re.search(
        r"(?:under|below|max|upto|up to|less than|within|budget(?:\s+of)?)\s*(?:rs\.?|inr|₹)?\s*(\d{2,6})",
        lowered,
    )
    if not price_match:
        price_match = re.search(r"(?:rs\.?|inr|₹)\s*(\d{2,6})", lowered)
    if price_match:
        max_price = float(price_match.group(1))

    attributes: list[str] = []
    for attr, words in ATTRIBUTE_WORDS.items():
        if any(word in lowered for word in words):
            attributes.append(attr)

    stop = {
        "under", "below", "with", "that", "this", "want", "need", "find", "buy",
        "me", "a", "an", "the", "for", "and", "or", "rs", "inr", "please", "looking",
    }
    keywords = [
        token
        for token in re.findall(r"[a-z0-9-]+", lowered)
        if token not in stop and not token.isdigit() and len(token) > 2
    ]
    return ParsedGoal(
        category=category,
        max_price_inr=max_price,
        keywords=keywords[:8],
        must_have_attributes=attributes,
        notes="deterministic parser",
    )


def validate_parsed_goal(data: dict[str, Any]) -> ParsedGoal:
    try:
        return ParsedGoal.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"LLM goal output failed schema validation: {exc}") from exc
