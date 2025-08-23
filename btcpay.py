# btcpay.py
"""
BTCPay helper module for the Escrow bot.

Environment variables required (set these in your .env):
  BTCPAY_URL       – e.g. https://mainnet.demo.btcpayserver.org
  BTCPAY_API_KEY   – API key created in your BTCPay account
  BTCPAY_STORE_ID  – Store ID where invoices are created

Optional (for local dry tests in this file):
  RUN_BTCPAY_TESTS=1

Notes
-----
• Do NOT hardcode secrets or URLs directly in code. Always read from .env.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional
import io

import requests
import qrcode
from dotenv import load_dotenv

load_dotenv()

# Load from environment variables
BTCPAY_URL = (os.getenv("BTCPAY_URL", "https://mainnet.demo.btcpayserver.org").rstrip("/"))
BTCPAY_API_KEY = os.getenv("BTCPAY_API_KEY")
BTCPAY_STORE_ID = os.getenv("BTCPAY_STORE_ID")


# --------------------------- Internal helpers ---------------------------

def _require_env() -> None:
    missing = [
        name
        for name, val in (
            ("BTCPAY_API_KEY", BTCPAY_API_KEY),
            ("BTCPAY_STORE_ID", BTCPAY_STORE_ID),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing env var(s): {', '.join(missing)}. Add them to your .env file."
        )


def _headers() -> Dict[str, str]:
    _require_env()
    return {
        "Authorization": f"token {BTCPAY_API_KEY}",
        "Content-Type": "application/json",
    }


def _store_base_url() -> str:
    return f"{BTCPAY_URL}/api/v1/stores/{BTCPAY_STORE_ID}"


# ------------------------------- Public API ------------------------------

def create_invoice(
    escrow_id: str,
    amount: float,
    currency: str = "USD",
    buyer_email: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{_store_base_url()}/invoices"
    payload: Dict[str, Any] = {
        "amount": str(amount),
        "currency": currency,
        "metadata": {"escrow_id": escrow_id},
    }
    if buyer_email:
        payload["metadata"]["buyerEmail"] = buyer_email

    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_invoice(invoice_id: str) -> Dict[str, Any]:
    url = f"{_store_base_url()}/invoices/{invoice_id}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def is_invoice_paid(invoice_id: str) -> bool:
    inv = get_invoice(invoice_id)
    return inv.get("status") == "Settled"


def generate_payment_qr(invoice_id: str) -> io.BytesIO:
    """
    Generate a QR code PNG for the first crypto payment address of an invoice.
    Returns a BytesIO object that you can send directly in your bot.
    """
    inv = get_invoice(invoice_id)

    # Extract payment address from first crypto method
    pm = inv.get("checkout", {}).get("paymentMethods", [])
    if not pm:
        raise ValueError("No payment methods found in invoice.")

    address = pm[0].get("destination")
    if not address:
        raise ValueError("No payment address found in invoice.")

    # Encode as Bitcoin URI (BIP21 style)
    amount = pm[0].get("amount")
    uri = f"bitcoin:{address}"
    if amount:
        uri += f"?amount={amount}"

    # Generate QR code into memory
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ------------------------------ Dry-run tests -----------------------------
def _run_dry_tests() -> None:
    global BTCPAY_URL, BTCPAY_API_KEY, BTCPAY_STORE_ID
    old = (BTCPAY_URL, BTCPAY_API_KEY, BTCPAY_STORE_ID)
    try:
        BTCPAY_URL = "https://example.com"
        BTCPAY_API_KEY = "test_api_key"
        BTCPAY_STORE_ID = "store_123"

        h = _headers()
        assert h["Authorization"] == "token test_api_key"
        assert h["Content-Type"] == "application/json"

        base = _store_base_url()
        assert base == "https://example.com/api/v1/stores/store_123"

        print("btcpay.py dry tests: PASS")
    finally:
        BTCPAY_URL, BTCPAY_API_KEY, BTCPAY_STORE_ID = old


if __name__ == "__main__":
    if os.getenv("RUN_BTCPAY_TESTS") == "1":
        _run_dry_tests()
