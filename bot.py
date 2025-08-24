# bot.py
import os
import asyncio
import io
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from aiogram.utils import executor
from dotenv import load_dotenv
import qrcode
import requests

# ---------------------- Load environment ----------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
TOPIC_IDS = [int(t.strip()) for t in os.getenv("TOPIC_IDS", "").split(",") if t.strip()]

BTCPAY_URL = os.getenv("BTCPAY_URL", "https://mainnet.demo.btcpayserver.org").rstrip("/")
BTCPAY_API_KEY = os.getenv("BTCPAY_API_KEY")
BTCPAY_STORE_ID = os.getenv("BTCPAY_STORE_ID")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# In-memory store for registered users
user_roles = {}  # {user_id: {"role": "seller"/"buyer", "address": "wallet"}}


# ---------------------- BTCPay Helpers ----------------------
def _headers():
    return {"Authorization": f"token {BTCPAY_API_KEY}", "Content-Type": "application/json"}


def _store_base_url():
    return f"{BTCPAY_URL}/api/v1/stores/{BTCPAY_STORE_ID}"


def get_invoice(invoice_id: str):
    url = f"{_store_base_url()}/invoices/{invoice_id}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def generate_payment_qr(invoice_id: str) -> io.BytesIO:
    inv = get_invoice(invoice_id)
    pm = inv.get("checkout", {}).get("paymentMethods", [])
    if not pm:
        raise ValueError("No payment methods in invoice")

    address = pm[0].get("destination")
    amount = pm[0].get("amount")
    uri = f"bitcoin:{address}"
    if amount:
        uri += f"?amount={amount}"

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------------- Group Invite ----------------------
async def generate_group_invite():
    if not TOPIC_IDS:
        raise ValueError("No topic IDs in .env")
    topic_id = random.choice(TOPIC_IDS)
    invite = await bot.create_chat_invite_link(
        chat_id=GROUP_CHAT_ID,
        name=f"Escrow Topic {topic_id}",
        creates_join_request=False
    )
    return invite.invite_link


# ---------------------- Commands ----------------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💬 INSTRUCTIONS", url="https://t.me/WealthEscrow/11"),
        InlineKeyboardButton("📜 TERMS", url="https://t.me/WealthEscrow/12"),
    )
    keyboard.add(
        InlineKeyboardButton("⚡️ CREATE ESCROW GROUP", callback_data="create_group"),
    )

    welcome = (
        "⚜️ <b>WealthEscrowBot</b> ⚜️ v.1\n"
        "Your Automated Telegram Escrow Service\n\n"
        "Welcome to WealthEscrowBot! This bot provides a secure escrow service for your transactions on Telegram. 🔒 "
        "No more worries about getting scammed—your funds stay safe during all your deals. "
        "If you run into any issues, just type <b>/contact</b>, and an arbitrator will join your group chat within 24 hours. ⏳\n\n"

        "💰 <b>ESCROW FEE:</b>\n"
        "5% for amounts over $100\n"
        "$5 for amounts under $100\n\n"

        "🌟 <a href='https://t.me/WealthEscrow'>UPDATES</a> - "
        "<a href='https://t.me/WealthEscrowBotVouches'>VOUCHES</a>\n"
        "✅ DEALS COMPLETED: 4371\n"
        "⚖️ DISPUTES RESOLVED: 162\n\n"

        "🛒 To declare yourself as a seller or buyer:\n"
        "Type <b>/seller ADDRESS</b> to register as a seller.\n"
        "Type <b>/buyer ADDRESS</b> to register as a buyer.\n"
        "• Or simply paste your crypto address and choose your role using the buttons.\n\n"

        "💡 Replace ADDRESS with your BTC, LTC, USDT (TRC20), USDT (BEP20), or TON wallet address.\n\n"
        "📜 Type <b>/menu</b> to view all the bot's features. (only in escrow group)"
    )

    await message.answer(welcome, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query_handler(lambda c: c.data == "create_group")
async def callback_create_group(call: types.CallbackQuery):
    invite = await generate_group_invite()
    await call.message.answer(f"⚡ Here is your private escrow group link:\n{invite}")


@dp.message_handler(commands=["create"])
async def cmd_create(message: types.Message):
    invite = await generate_group_invite()
    await message.answer(f"⚡ Here is your private escrow group link:\n{invite}")


@dp.message_handler(commands=["pay"])
async def cmd_pay(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ Usage: /pay <invoice_id>")
        return

    invoice_id = parts[1]
    try:
        inv = get_invoice(invoice_id)
        checkout_url = inv.get("checkoutLink")
        qr_buf = generate_payment_qr(invoice_id)

        msg = await message.answer_photo(
            types.InputFile(qr_buf, filename="qr.png"),
            caption=f"💳 <b>Invoice Payment</b>\n"
                    f"ID: <code>{invoice_id}</code>\n\n"
                    f"Pay here: {checkout_url}\n\n"
                    f"(This message will auto-delete in 60s)"
        )

        await asyncio.sleep(60)
        await msg.delete()
        await message.delete()
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@dp.message_handler(commands=["menu"])
async def cmd_menu(message: types.Message):
    text = (
        "📜 <b>Bot Menu</b>\n\n"
        "/whatisescrow - Explains escrow\n"
        "/video - Sends bot working video\n"
        "/balance - Show escrow balance\n"
        "/pay_seller - Releases money to seller\n"
        "/refund_buyer - Releases money to buyer\n"
        "/qr - Show address QR\n"
        "/blockchain - Show blockchain link of address\n"
        "/contact - Contact an admin in case of dispute\n"
        "/real - Check if admin is real\n"
        "/review - To leave a review\n"
        "/userinfo - Get detailed escrow stats\n"
        "/leaderboard - View Top Users\n"
        "/refer - Refer users and earn USDT bonuses\n"
        "/setpin - Set Transaction PIN\n"
    )
    await message.answer(text, parse_mode="HTML")


# ---------------------- Seller / Buyer ----------------------
@dp.message_handler(commands=["seller"])
async def cmd_seller(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ Usage: /seller <WALLET_ADDRESS>")
        return

    wallet = parts[1]
    user_roles[message.from_user.id] = {"role": "seller", "address": wallet}
    await message.reply(f"✅ You are now registered as a <b>SELLER</b>.\nWallet: <code>{wallet}</code>", parse_mode="HTML")


@dp.message_handler(commands=["buyer"])
async def cmd_buyer(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ Usage: /buyer <WALLET_ADDRESS>")
        return

    wallet = parts[1]
    user_roles[message.from_user.id] = {"role": "buyer", "address": wallet}
    await message.reply(f"✅ You are now registered as a <b>BUYER</b>.\nWallet: <code>{wallet}</code>", parse_mode="HTML")


# ---------------------- Register Bot Commands ----------------------
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="whatisescrow", description="Explains escrow"),
        BotCommand(command="video", description="Sends bot working video"),
        BotCommand(command="balance", description="Show escrow balance"),
        BotCommand(command="pay_seller", description="Releases money to seller"),
        BotCommand(command="refund_buyer", description="Releases money to buyer"),
        BotCommand(command="qr", description="Show address QR"),
        BotCommand(command="blockchain", description="Show blockchain link of address"),
        BotCommand(command="contact", description="Contact an admin in case of dispute"),
        BotCommand(command="real", description="Check if admin is real"),
        BotCommand(command="review", description="To leave a review"),
        BotCommand(command="userinfo", description="Get detailed escrow stats"),
        BotCommand(command="leaderboard", description="View Top Users"),
        BotCommand(command="refer", description="Refer users and earn USDT bonuses"),
        BotCommand(command="setpin", description="Set Transaction PIN"),
        BotCommand(command="menu", description="View all bot features"),
        BotCommand(command="seller", description="Register as seller with wallet"),
        BotCommand(command="buyer", description="Register as buyer with wallet"),
    ]
    await bot.set_my_commands(commands)


# ---------------------- Startup ----------------------
async def on_startup(dp):
    await set_bot_commands(bot)
    print("✅ WealthEscrowBot started...")


if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
