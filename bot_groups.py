# bot_groups.py
import os
import random
import io
import requests
import qrcode
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import FSInputFile, Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram import Router

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
TOPIC_IDS = [int(t.strip()) for t in os.getenv("TOPIC_IDS", "").split(",") if t.strip()]

BTCPAY_URL = (os.getenv("BTCPAY_URL", "https://mainnet.demo.btcpayserver.org").rstrip("/"))
BTCPAY_API_KEY = os.getenv("BTCPAY_API_KEY")
BTCPAY_STORE_ID = os.getenv("BTCPAY_STORE_ID")

if not BOT_TOKEN:
    raise RuntimeError("❌ Missing BOT_TOKEN in .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -------------------------------------------------------------------
# BTCPay helper functions
# -------------------------------------------------------------------

def _headers():
    if not BTCPAY_API_KEY or not BTCPAY_STORE_ID:
        raise RuntimeError("❌ Missing BTCPAY_API_KEY or BTCPAY_STORE_ID in .env")
    return {
        "Authorization": f"token {BTCPAY_API_KEY}",
        "Content-Type": "application/json",
    }

def _store_base_url() -> str:
    return f"{BTCPAY_URL}/api/v1/stores/{BTCPAY_STORE_ID}"

def create_invoice(escrow_id: str, amount: float, currency: str = "USD") -> dict:
    url = f"{_store_base_url()}/invoices"
    payload = {
        "amount": str(amount),
        "currency": currency,
        "metadata": {"escrow_id": escrow_id},
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()

def get_invoice(invoice_id: str) -> dict:
    url = f"{_store_base_url()}/invoices/{invoice_id}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()

def generate_payment_qr(invoice_id: str, prefer_lightning: bool = False) -> tuple[io.BytesIO, str]:
    """
    Return (qr_buffer, payment_uri) for BTC or LN based on preference.
    """
    inv = get_invoice(invoice_id)

    methods = inv.get("checkout", {}).get("paymentMethods", [])
    if not methods:
        raise ValueError("No payment methods found in invoice.")

    chosen = None
    if prefer_lightning:
        for m in methods:
            if "Lightning" in m.get("paymentMethod", ""):
                chosen = m
                break
    if not chosen:
        chosen = methods[0]

    address = chosen.get("destination")
    if not address:
        raise ValueError("No payment destination found.")

    amount = chosen.get("amount")
    if "Lightning" in chosen.get("paymentMethod", ""):
        uri = f"lightning:{address}"
    else:
        uri = f"bitcoin:{address}"
        if amount:
            uri += f"?amount={amount}"

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, uri

# -------------------------------------------------------------------
# Bot commands
# -------------------------------------------------------------------

@dp.message(Command("create"))
async def cmd_create(message: Message):
    """
    Generate a fresh invite link to the group, assigning it to a random topic.
    """
    if not TOPIC_IDS:
        await message.reply("❌ No topic IDs configured in .env")
        return

    topic_id = random.choice(TOPIC_IDS)
    invite = await bot.create_chat_invite_link(
        chat_id=GROUP_CHAT_ID,
        name=f"Escrow Topic {topic_id}",
        creates_join_request=False
    )
    await message.reply(f"✅ Invite link created for topic {topic_id}:\n{invite.invite_link}")

@dp.message(Command("pay"))
async def cmd_pay(message: Message):
    """
    Generate and send a QR code for a BTCPay invoice.
    Usage: /pay <invoice_id>
    """
    args = message.text.strip().split()
    if len(args) < 2:
        await message.reply("⚠️ Usage: /pay <invoice_id>")
        return

    invoice_id = args[1]

    try:
        qr_buf, uri = generate_payment_qr(invoice_id, prefer_lightning=False)

        tmp_file = f"/tmp/{invoice_id}.png"
        with open(tmp_file, "wb") as f:
            f.write(qr_buf.read())

        photo = FSInputFile(tmp_file)
        await message.reply_photo(
            photo,
            caption=f"💳 Payment QR for invoice `{invoice_id}`\n\n👉 URI: `{uri}`",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------------------------------------------------------
# Run the bot
# -------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())
