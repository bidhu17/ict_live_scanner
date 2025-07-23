import pandas as pd
import time
from datetime import datetime, timedelta
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import os
from kite_token_manager import initialize_kite

# --- ✅ Initialize Kite ---
kite = initialize_kite()

# --- 📦 Load NSE Instruments ---
instruments = pd.DataFrame(kite.instruments("NSE"))

# ✅ Normalize symbols
instruments['tradingsymbol_clean'] = instruments['tradingsymbol'].str.strip().str.upper()

nifty_50 = [
    'ADANIPORTS', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV',
    'BPCL', 'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DIVISLAB', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK',
    'ITC', 'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI',
    'NTPC', 'NESTLEIND', 'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN', 'SUNPHARMA',
    'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 'TECHM', 'TITAN', 'ULTRACEMCO',
    'UPL', 'WIPRO', 'HEROMOTOCO', 'HDFCLIFE', 'HINDPETRO', 'ADANIENT'
]
nifty_50_clean = [s.strip().upper() for s in nifty_50]

# ✅ Correct token mapping
symbol_tokens = {}
for sym in nifty_50_clean:
    token_row = instruments[instruments['tradingsymbol_clean'] == sym]
    if not token_row.empty:
        symbol_tokens[sym] = int(token_row.iloc[0]['instrument_token'])

print("✅ Loaded tokens:", symbol_tokens)
print("✅ INFY token (final):", symbol_tokens.get('INFY'))
print(instruments[instruments['tradingsymbol_clean'] == 'INFY'])

# --- 📂 Load POI ---
poi_df = pd.read_csv("poi_2025-07-23.csv")

# 🔁 Add mock POI for INFY to force alert
mock_row = pd.DataFrame([{
    'symbol': 'INFY',
    'type': 'OB',
    'low': 1,
    'high': 99999
}])
poi_df = pd.concat([poi_df, mock_row], ignore_index=True)
print("✅ Mock POI added for INFY")

alert_log = []
alert_file = "alert_log.csv"
if os.path.exists(alert_file):
    alert_log = pd.read_csv(alert_file).to_dict("records")
    print(f"✅ Loaded {len(alert_log)} past alerts")
else:
    print("🆕 No previous alert log found")

# --- Detection logic ---
def detect_choch_bos(df):
    choch_15m = choch_5m = bos_5m = False
    def has_choch(d):
        d = d.sort_values('date')
        return len(d) >= 6 and d['low'].iloc[-1] < d['low'].iloc[-3] and d['high'].iloc[-1] > d['high'].iloc[-5]
    def has_bos(d):
        d = d.sort_values('date')
        return len(d) >= 6 and (d['high'].iloc[-1] >= d['high'].max() * 0.999 or d['low'].iloc[-1] <= d['low'].min() * 1.001)
    df_15m = df[df['interval'] == '15minute']
    df_5m = df[df['interval'] == '5minute']
    if not df_15m.empty: choch_15m = has_choch(df_15m)
    if not df_5m.empty:
        choch_5m = has_choch(df_5m)
        bos_5m = has_bos(df_5m)
    return choch_15m, choch_5m, bos_5m

# --- Fetch historical data ---
def get_recent_data(symbol):
    token = symbol_tokens.get(symbol)
    if not token: return pd.DataFrame()
    df_all = []
    for interval in ['15minute', '5minute']:
        try:
            print(f"⏳ Fetching historical for {symbol} [{interval}]...")
            data = kite.historical_data(token, datetime.now() - timedelta(days=3), datetime.now(), interval)
            df = pd.DataFrame(data)
            df['interval'] = interval
            df['date'] = pd.to_datetime(df['date'])
            df_all.append(df)
            print(f"✅ {symbol} [{interval}] fetched: {len(df)} candles")
        except Exception as e:
            print(f"⚠️ {symbol} fetch failed: {e}")
    return pd.concat(df_all) if df_all else pd.DataFrame()

# --- LTP fetch ---
def fetch_ltp(symbols):
    all_ltp = {}
    for i in range(0, len(symbols), 10):
        batch = symbols[i:i + 10]
        try:
            print(f"📡 Fetching batch: {batch}")
            res = kite.ltp(batch)
            print(f"✅ Response keys: {list(res.keys())}")
            all_ltp.update(res)
        except Exception as e:
            print(f"❌ LTP fetch failed for batch {batch}: {e}")
    return all_ltp

# --- Dash Setup ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "ICT Alert Dashboard"

app.layout = html.Div(style={'backgroundColor': '#0D1B2A', 'padding': '20px'}, children=[
    html.H1("ICT Multi-Timeframe Dashboard", style={"color": "#FFD700"}),
    dcc.Interval(id="interval", interval=5 * 60 * 1000, n_intervals=0),
    dash_table.DataTable(
        id='live-table',
        columns=[
            {'name': 'Time', 'id': 'time'},
            {'name': 'Symbol', 'id': 'symbol'},
            {'name': 'Zone Type', 'id': 'type'},
            {'name': 'Zone Low', 'id': 'low'},
            {'name': 'Zone High', 'id': 'high'},
            {'name': 'LTP', 'id': 'ltp'},
            {'name': 'CHoCH_15m', 'id': 'choch_15m'},
            {'name': 'CHoCH_5m', 'id': 'choch_5m'},
            {'name': 'BOS_5m', 'id': 'bos_5m'},
        ],
        data=[]
    )
])

@app.callback(Output('live-table', 'data'), Input('interval', 'n_intervals'))
def update_alert_table(n):
    global alert_log
    unique_symbols = poi_df['symbol'].unique()
    ltp_data = fetch_ltp([f"NSE:{sym}" for sym in unique_symbols if sym in symbol_tokens])
    print("🔎 LTP data keys:", list(ltp_data.keys()))
    for _, row in poi_df.iterrows():
        symbol, ztype, low, high = row['symbol'], row['type'], row['low'], row['high']
        ltp = ltp_data.get(f"NSE:{symbol}", {}).get("last_price")
        if not ltp:
            print(f"⚠️ {symbol} LTP not found")
            continue
        in_zone = low <= ltp <= high
        if not in_zone:
            continue
        df = get_recent_data(symbol)
        choch_15m, choch_5m, bos_5m = detect_choch_bos(df)
        print(f"✅ {symbol} ALERT! CHoCH_15m={choch_15m}, BOS_5m={bos_5m}")
        alert = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'type': ztype,
            'low': round(low, 2),
            'high': round(high, 2),
            'ltp': round(ltp, 2),
            'choch_15m': '✅' if choch_15m else '❌',
            'choch_5m': '✅' if choch_5m else '❌',
            'bos_5m': '✅' if bos_5m else '❌',
        }
        alert_log.append(alert)
        pd.DataFrame(alert_log).to_csv(alert_file, index=False)
    return alert_log[::-1]

if __name__ == '__main__':
    app.run(debug=True)
