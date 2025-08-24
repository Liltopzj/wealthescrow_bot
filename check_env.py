import os
from dotenv import load_dotenv

load_dotenv()  # load from .env

print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))
print("ADMIN_ID:", os.getenv("ADMIN_ID"))
print("BTCPAY_API_KEY:", os.getenv("BTCPAY_API_KEY"))
print("TG_API_ID:", os.getenv("TG_API_ID"))
print("TG_API_HASH:", os.getenv("TG_API_HASH"))
