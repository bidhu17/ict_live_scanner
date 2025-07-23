# kite_token_manager.py
import os
import json
from kiteconnect import KiteConnect

# --- Kite API Credentials ---
api_key = "dvnc9fl5v85ilab5"
api_secret = "q3vs6e40p3j8832vdmhdh23b2gfwnflo"
token_path = "access_token.json"

kite = KiteConnect(api_key=api_key)

def initialize_kite():
    if not os.path.exists(token_path):
        raise Exception("❌ access_token.json not found. Please run kite_token_generator.py first.")

    with open(token_path, "r") as f:
        token_data = json.load(f)
        access_token = token_data.get("access_token")

    try:
        kite.set_access_token(access_token)
        kite.profile()  # Validate token
        print("✅ Access token is valid.")
        return kite
    except Exception as e:
        raise Exception(f"❌ Token invalid: {e}")
