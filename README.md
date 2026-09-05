# Agentic Commerce Demo

Stride Lab is a hackathon demo of an **AI-readable merchant** plus a **buyer agent**, with a **hard policy gate** in front of money. The LLM may parse a shopping goal. It may **not** approve spend.

## Architecture

```
[Human]
   ↓ (goal + budget)
[Buyer Agent] ←→ [Catalog API] ←→ [Merchant catalog JSON / SQLite]
   ↓
[Policy Gate] ←——————— [Upsell Agent]
   ↓
[Razorpay test-mode or mock]
   ↓
[SQLite audit log] → [Demo UI]
```

Every actor writes the same audit table. The UI plays that table back as one timeline.

**Determinism:** `gate/policy_gate.py`, `buyer_agent/ranker.py`, and upsell `rules.py` are plain Python. Checkout amounts come from cart paise, not from model text.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Open http://127.0.0.1:8000

Optional `.env` (copy `.env.example`):

- `ANTHROPIC_API_KEY` — Claude parses the goal; otherwise a deterministic parser is used.
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — creates a real **test-mode order**. Card collection is simulated so the demo does not need Checkout.js. If keys are missing, order ids are mocked.

```bash
pytest -q
```

## Judge demo script

1. **Happy path:** preset “Happy path” → Run. Watch parse → rank → gate approve → upsell → Razorpay capture. Point at **growth lift**.
2. **Audit trail:** same run; every money action has `approve` / `reject` and a reason.
3. **Failure:** check “Simulate Razorpay decline” → Run. One retry, then a clean stop, cart not charged.
4. **Gate proof:** preset “Over-budget reject” or set max spend to `100` with the running-shoes goal. Timeline shows `policy_gate` **reject** on `max_total_spend`.
5. **One-liner:** *Cart total plus any upsell must stay under the human spend cap; a single upsell must stay under the upsell cap. The model cannot bypass that.*

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/catalog` | AI-readable product list |
| GET | `/product/{id}` | Single SKU |
| GET | `/capabilities` | Allowed agent actions |
| POST | `/api/run` | Full session: goal, budget, optional decline |

## Layout

Matches the planned packages: `merchant/`, `buyer_agent/`, `upsell_agent/`, `gate/`, `payments/`, `audit/`, `orchestrator/`, `frontend/`, `tests/`.
