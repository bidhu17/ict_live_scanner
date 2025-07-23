# === ✅ FILE 2: generate_poi.py ===
import os
import json
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# === ⚙️ Kite Credentials ===
api_key = "dvnc9fl5v85ilab5"
api_secret = "q3vs6e40p3j8832vdmhdh23b2gfwnflo"
token_path = "access_token.json"

kite = KiteConnect(api_key=api_key)

# === 🔐 Load Access Token ===
if os.path.exists(token_path):
    with open(token_path, "r") as f:
        token_data = json.load(f)
        access_token = token_data.get("access_token")
        print("🔑 Loaded access token:", access_token)
        try:
            kite.set_access_token(access_token)
            profile = kite.profile()
            print("✅ Token is valid for:", profile['user_name'])
        except Exception as e:
            print("❌ Token check failed:", e)
            exit()
else:
    print("❌ access_token.json not found.")
    exit()

# === 📦 Load Instruments ===
instruments = pd.DataFrame(kite.instruments("NSE"))
instruments['tradingsymbol_clean'] = instruments['tradingsymbol'].str.strip().str.upper()

nifty_50 = [
    'ADANIPORTS','ASIANPAINT','AXISBANK','BAJAJ-AUTO','BAJFINANCE','BAJAJFINSV','BPCL',
    'BHARTIARTL','BRITANNIA','CIPLA','COALINDIA','DIVISLAB','DRREDDY','EICHERMOT','GRASIM',
    'HCLTECH','HDFCBANK','HINDALCO','HINDUNILVR','ICICIBANK','ITC','INDUSINDBK','INFY',
    'JSWSTEEL','KOTAKBANK','LT','M&M','MARUTI','NTPC','NESTLEIND','ONGC','POWERGRID',
    'RELIANCE','SBILIFE','SBIN','SUNPHARMA','TCS','TATACONSUM','TATAMOTORS','TATASTEEL',
    'TECHM','TITAN','ULTRACEMCO','UPL','WIPRO','HEROMOTOCO','HDFCLIFE','HINDPETRO','ADANIENT'
]
nifty_50 = [s.strip().upper() for s in nifty_50]

symbol_tokens = {}
for sym in nifty_50:
    row = instruments[instruments['tradingsymbol_clean'] == sym]
    if not row.empty:
        symbol_tokens[sym] = int(row.iloc[0]['instrument_token'])

# === 📈 POI Detection ===
def detect_order_blocks(df):
    ob_zones = []
    for i in range(2, len(df)):
        if df['close'][i - 1] < df['open'][i - 1] and df['close'][i] > df['open'][i]:
            low = df['low'][i - 1]
            high = df['high'][i - 1]
            ob_zones.append(('OB', low, high))
    return ob_zones

def detect_fvg(df):
    fvg_zones = []
    for i in range(2, len(df)):
        if df['low'][i] > df['high'][i - 2]:
            fvg_zones.append(('FVG', df['high'][i - 2], df['low'][i]))
    return fvg_zones

# === 📅 Fetch Historical Data ===
to_date = datetime.now()
from_date = to_date - timedelta(days=365)
poi_rows = []

for symbol, token in symbol_tokens.items():
    print(f"📊 Processing {symbol}...")
    try:
        df = pd.DataFrame(kite.historical_data(token, from_date, to_date, "day"))
        df = df[['date', 'open', 'high', 'low', 'close']]

        ob = detect_order_blocks(df)
        fvg = detect_fvg(df)

        for typ, low, high in ob + fvg:
            poi_rows.append({
                'symbol': symbol,
                'type': typ,
                'low': round(low, 2),
                'high': round(high, 2)
            })

    except Exception as e:
        print(f"⚠️ {symbol} failed:", e)

# === 💾 Save POI CSV ===
poi_df = pd.DataFrame(poi_rows)
poi_file = f"poi_{to_date.strftime('%Y-%m-%d')}.csv"
poi_df.to_csv(poi_file, index=False)
print(f"✅ POI saved to: {poi_file}")
