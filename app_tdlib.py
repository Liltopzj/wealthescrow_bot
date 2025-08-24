# app_tdlib.py
import os
import asyncio
import random
import string

from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import ChatPrivileges

# ── ENV ────────────────────────────────────────────────────────────────────────
# REQUIRED in .env:
#   BOT_TOKEN=123456:ABC...
#   TG_API_ID=29198449
#   TG_API_HASH=1531c0...
#   USER_SESSION_STRING=<<< your long base64 session string >>>
# OPTIONAL:
#   GROUP_BASE_NAME=Escrow
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()
API_ID  = int(os.getenv("TG_API_ID", "0") or "0")
API_HASH = os.getenv("TG_API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
USER_SESSION_STRING = os.getenv("USER_SESSION_STRING", "")
GROUP_BASE_NAME = os.getenv("GROUP_BASE_NAME", "Escrow")

if not (API_ID and API_HASH and BOT_TOKEN):
    raise RuntimeError("Missing TG_API_ID / TG_API_HASH / BOT_TOKEN in .env")
if not USER_SESSION_STRING:
    raise RuntimeError("Missing USER_SESSION_STRING in .env (your phone login)")

# ── CLIENTS ───────────────────────────────────────────────────────────────────
# Bot client (receives /create)
bot = Client(
    name="escrow_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# User client (your logged-in account creates groups)
user = Client(
    name="escrow_user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=USER_SESSION_STRING,
)

BOT_USERNAME_CACHE = None  # filled on startup

# ── UTILS ─────────────────────────────────────────────────────────────────────
def generate_suffix(length: int = 5) -> str:
    """Generate random group suffix like jqbdp."""
    import string as _s, random as _r
    alphabet = _s.ascii_lowercase
    return "".join(_r.choice(alphabet) for _ in range(length))

async def create_new_group() -> tuple[str, str, int]:
    """
    Create a brand-new supergroup via the USER session, invite the BOT,
    export an invite link, and return (invite_link, title, chat_id).
    """
    # Ensure we know the bot username once
    global BOT_USERNAME_CACHE
    if not BOT_USERNAME_CACHE:
        me = await bot.get_me()
        BOT_USERNAME_CACHE = me.username  # without '@'

    # Title like: Escrow #abcde
    code = generate_suffix(5)
    title = f"{GROUP_BASE_NAME} #{code}"

    # 1) Create supergroup as USER
    chat = await user.create_supergroup(title=title, description="Escrow room created by WealthEscrowBot")

    # 2) Invite the BOT into the new group
    try:
        await user.add_chat_members(chat_id=chat.id, user_ids=[f"@{BOT_USERNAME_CACHE}"])
    except Exception:
        # If already in or invite by link only, ignore
        pass

    # (optional) Promote bot with basic admin powers
    try:
        await user.promote_chat_member(
            chat_id=chat.id,
            user_id=f"@{BOT_USERNAME_CACHE}",
            privileges=ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_restrict_members=True,
                can_change_info=True,
                can_promote_members=False,
            ),
        )
    except Exception:
        pass

    # 3) Export invite link (multi-use)
    try:
        invite_link = await user.export_chat_invite_link(chat.id)
    except Exception:
        inv = await user.create_chat_invite_link(chat.id)
        invite_link = inv.invite_link

    return invite_link, title, chat.id

# ── HANDLERS (keep your original flow, just powered by USER session) ──────────
@bot.on_message(filters.command("create") & filters.private)
async def handle_create(_, message):
    await message.reply("Creating Escrow Group. Please Wait...")

    try:
        link, title, chat_id = await create_new_group()

        # Reply to the user with link (same style you had)
        await message.reply(
            f"✅ Created Escrow Group <b>{title}</b>\n\n"
            f"🔗 Group Link: {link}\n\n"
            "Now join this escrow group & forward this message to buyer/seller.\n\n"
            "Enjoy Safe Escrow 🍻",
            disable_web_page_preview=True,
        )

        # Post welcome + admin note inside the new group (from BOT)
        await bot.send_message(
            chat_id,
            f"👋 Welcome to <b>{title}</b>!\n\n"
            f"This group has been created for your escrow transaction. "
            f"Please follow the guidelines below carefully."
        )

        await bot.send_message(
            chat_id,
            "⚖️ <b>Important Notice</b> ⚖️\n\n"
            "In Wealth Escrow groups, our admins @mruppy and @cheflatto can join at any time to ensure everything "
            "runs smoothly and securely. While our escrow process is fully automated through the bot, we also have "
            "active manual monitoring to keep transactions safe.\n\n"
            "🚨 <b>Important:</b> Escrow groups are only for depositing and releasing payments. "
            "All product discussions and deliveries should be handled privately in DMs."
        )

    except Exception as e:
        await message.reply(f"❌ Error creating group: {e}")

# (Optional) keep your legacy /start here if you want the bot to greet in DM
@bot.on_message(filters.command("start") & filters.private)
async def handle_start(_, message):
    await message.reply("Welcome! Use /create to open a fresh escrow group.")

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    # Start both clients
    await user.start()
    await bot.start()

    # Cache bot username (used when inviting)
    global BOT_USERNAME_CACHE
    me = await bot.get_me()
    BOT_USERNAME_CACHE = me.username

    print("Bot is running...")
    await idle()  # keep both running

    # Graceful shutdown
    await bot.stop()
    await user.stop()

if __name__ == "__main__":
    asyncio.run(main())
