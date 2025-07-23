# === ✅ FILE 1: kite_token_generator.py ===
import os
import json
from kiteconnect import KiteConnect

# === ⚙️ Kite Credentials ===
api_key = "dvnc9fl5v85ilab5"
api_secret = "q3vs6e40p3j8832vdmhdh23b2gfwnflo"
token_path = "access_token.json"

kite = KiteConnect(api_key=api_key)

print("🔐 Please login to Kite in the browser...")
print("🌐 Login URL:", kite.login_url())

request_token = input("🔑 Paste request token here: ")
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

with open(token_path, "w") as f:
    json.dump({
        "access_token": data["access_token"],
        "login_time": str(data["login_time"])
    }, f)

print("✅ Access token generated and saved.")