from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("AUDIT_DB_PATH") or (ROOT / "audit" / "audit_store.db"))
CATALOG_PATH = ROOT / "merchant" / "catalog_data.json"
CAPABILITIES_PATH = ROOT / "merchant" / "capabilities.json"
BUDGET_CONFIG_PATH = ROOT / "buyer_agent" / "budget_config.json"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
