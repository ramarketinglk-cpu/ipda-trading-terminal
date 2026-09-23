import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG & LAYOUT ---
st.set_page_config(
    page_title="IPDA Master Entry Engine",
    page_icon="🎯",
    layout="wide"
)

# Auto Refresh Every 60 Seconds for Background Scanning
st_autorefresh(interval=60 * 1000, key="ipda_bg_auto_refresh")

# --- 0. READ SECRETS AS PERMANENT DEFAULTS ---
secret_license = st.secrets.get("LICENSE_KEY", "") if "LICENSE_KEY" in st.secrets else ""
secret_tg_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "") if "TELEGRAM_BOT_TOKEN" in st.secrets else ""
secret_tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "") if "TELEGRAM_CHAT_ID" in st.secrets else ""

# --- QUERY PARAMS FOR BROWSER PERSISTENCE ---
query_params = st.query_params

# Retrieve initial values (Secrets > Query Params > Session State)
init_license = secret_license or query_params.get("license", [""])[0] if isinstance(query_params.get("license"), list) else query_params.get("license", "")
init_token = secret_tg_token or query_params.get("tg_token", [""])[0] if isinstance(query_params.get("tg_token"), list) else query_params.get("tg_token", "")
init_chat = secret_tg_chat_id or query_params.get("tg_chat", [""])[0] if isinstance(query_params.get("tg_chat"), list) else query_params.get("tg_chat", "")

# --- INITIALIZE SESSION STATE ---
if "saved_license_key" not in st.session_state:
    st.session_state.saved_license_key = init_license
if "saved_telegram_token" not in st.session_state:
    st.session_state.saved_telegram_token = init_token
if "saved_telegram_chat_id" not in st.session_state:
    st.session_state.saved_telegram_chat_id = init_chat
if "telegram_enabled" not in st.session_state:
    st.session_state.telegram_enabled = True if init_token and init_chat else False
if "selected_tg_coins" not in st.session_state:
    st.session_state.selected_tg_coins = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
if "sent_signals" not in st.session_state:
    st.session_state.sent_signals = set()

# --- SAAS LICENSE DATABASE ---
VALID_LICENSES = {
    "IPDA-ADMIN-2026":            {"type": "LIFETIME", "expiry": "2099-12-31", "owner": "Admin Master Key"},
    "IPDA-MONTHLY-USER1":         {"type": "MONTHLY",  "expiry": "2026-10-31", "owner": "Client A"},
    "IPDA-MONTHLY-USER2":         {"type": "MONTHLY",  "expiry": "2026-12-15", "owner": "Client B"},
    "IPDA-LIFETIME-VIP":          {"type": "LIFETIME", "expiry": "2099-12-31", "owner": "VIP Trader"},
}

def verify_license_key(key):
    clean_key = key.strip()
    if clean_key in VALID_LICENSES:
        user_info = VALID_LICENSES[clean_key]
        expiry_date = pd.to_datetime(user_info["expiry"]).date()
        today_date = pd.to_datetime("today").date()

        if today_date <= expiry_date:
            days_left = (expiry_date - today_date).days
            return True, user_info["type"], user_info["owner"], expiry_date, days_left, "ACTIVE"
        else:
            return False, user_info["type"], user_info["owner"], expiry_date, 0, "EXPIRED"
    return False, None, None, None, 0, "INVALID"

# --- SIDEBAR AUTHENTICATION ---
st.sidebar.header("🔑 Membership & License Auth")

input_license_key = st.sidebar.text_input(
    "Enter License Key", 
    value=st.session_state.saved_license_key,
    type="password", 
    help="WhatsApp us for License key +94750511732"
)

if input_license_key != st.session_state.saved_license_key:
    st.session_state.saved_license_key = input_license_key
    st.query_params["license"] = input_license_key

if not st.session_state.saved_license_key:
    st.title("🎯 IPDA Pro Master Entry")
    st.info("🔒 Please enter a valid License Key in the sidebar to access the Trading Engine.")
    st.stop()

is_valid, plan_type, owner_name, exp_date, days_remaining, status_code = verify_license_key(st.session_state.saved_license_key)

if not is_valid:
    if status_code == "EXPIRED":
        st.sidebar.error(f"❌ License Expired on {exp_date}!")
    else:
        st.sidebar.error("❌ Invalid License Key!")
    st.stop()

st.sidebar.success(f"✅ Active: {plan_type} ({owner_name})")

if st.sidebar.button("🚪 Logout / Reset Credentials"):
    st.session_state.saved_license_key = ""
    st.session_state.saved_telegram_token = ""
    st.session_state.saved_telegram_chat_id = ""
    st.session_state.telegram_enabled = False
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")

# --- TOP 50 PERPETUAL PAIRS ---
TOP_50_COINS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "BNB-USDT-SWAP", "XRP-USDT-SWAP",
    "DOGE-USDT-SWAP", "ADA-USDT-SWAP", "AVAX-USDT-SWAP", "LINK-USDT-SWAP", "SUI-USDT-SWAP",
    "NEAR-USDT-SWAP", "PEPE-USDT-SWAP", "APT-USDT-SWAP", "FET-USDT-SWAP", "LTC-USDT-SWAP",
    "DOT-USDT-SWAP", "SHIB-USDT-SWAP", "WIF-USDT-SWAP", "RENDER-USDT-SWAP", "TAO-USDT-SWAP"
]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎯 Pair & Strategy Settings")
selected_coin = st.sidebar.selectbox("Select Perpetual Pair (Visual Chart)", TOP_50_COINS, index=0)
execution_tf = st.sidebar.selectbox("Execution Timeframe", ["5m", "15m", "1h"], index=1)
htf_tf = "4h"

limit = st.sidebar.slider("Historical Candles Limit", min_value=100, max_value=1000, value=300)
risk_reward_target = st.sidebar.slider("Min Risk-to-Reward Ratio (RR)", 1.5, 5.0, 2.0, 0.5)

use_session_filter = st.sidebar.checkbox("Apply Session Kill Zone Filter", value=True)
use_htf_filter = st.sidebar.checkbox("Apply 4H HTF Trend Filter", value=True)

# Risk Management
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=10.0, value=1000.0, step=50.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
user_leverage = st.sidebar.number_input("Leverage (x)", min_value=1, max_value=125, value=10, step=1)

# --- TELEGRAM BOT SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.header("📲 Telegram Bot Settings")

enable_telegram = st.sidebar.checkbox("Enable Telegram Alerts", value=st.session_state.telegram_enabled)
st.session_state.telegram_enabled = enable_telegram

telegram_bot_token = st.sidebar.text_input("Bot Token", value=st.session_state.saved_telegram_token, type="password")
if telegram_bot_token != st.session_state.saved_telegram_token:
    st.session_state.saved_telegram_token = telegram_bot_token
    st.query_params["tg_token"] = telegram_bot_token

telegram_chat_id = st.sidebar.text_input("Chat ID", value=st.session_state.saved_telegram_chat_id)
if telegram_chat_id != st.session_state.saved_telegram_chat_id:
    st.session_state.saved_telegram_chat_id = telegram_chat_id
    st.query_params["tg_chat"] = telegram_chat_id

tg_selected_coins = st.sidebar.multiselect(
    "🔔 Select Coins for 24/7 Telegram Alerts",
    options=TOP_50_COINS,
    default=[c for c in st.session_state.selected_tg_coins if c in TOP_50_COINS]
)
st.session_state.selected_tg_coins = tg_selected_coins

# Telegram Dispatcher Function
def send_telegram_alert(token, chat_id, message):
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        pass

OKX_TF_MAP = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H"}

@st.cache_data(ttl=10)
def fetch_futures_data(inst_id, tf, limit=300):
    try:
        bar_tf = OKX_TF_MAP.get(tf, "15m")
        url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar_tf}&limit={limit}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        json_data = res.json()
        if json_data.get('code') != '0' or not json_data.get('data'):
            return pd.DataFrame()

        df = pd.DataFrame(json_data['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'VolCcy', 'VolCcyQuote', 'Confirm'])
        df = df.iloc[::-1].reset_index(drop=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Timestamp'] = pd.to_datetime(pd.to_numeric(df['Timestamp']), unit='ms', utc=True).dt.tz_convert('Asia/Colombo')
        df.set_index('Timestamp', inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception:
        return pd.DataFrame()

def calculate_htf_trend(df_htf):
    if df_htf.empty or len(df_htf) < 20:
        return "NEUTRAL"
    ema20 = df_htf['Close'].ewm(span=20, adjust=False).mean()
    return "BULLISH" if df_htf['Close'].iloc[-1] > ema20.iloc[-1] else "BEARISH"

def is_in_kill_zone(timestamp_slst):
    time_val = timestamp_slst.hour + (timestamp_slst.minute / 60.0)
    return (12.5 <= time_val <= 15.5) or (17.5 <= time_val <= 20.5)

def process_ipda_engine_v3(df, htf_trend, rr_ratio, session_filter, htf_filter, symbol_name):
    if df.empty or len(df) < 30:
        return df, []
    
    trade_signals = []
    highs, lows, closes = df['High'].values, df['Low'].values, df['Close'].values

    for i in range(20, len(df) - 1):
        t_time = df.index[i]
        if session_filter and not is_in_kill_zone(t_time):
            continue

        r_high, r_low = np.max(highs[i-20:i]), np.min(lows[i-20:i])
        is_sweep_high = highs[i] > r_high and closes[i] < r_high
        is_sweep_low = lows[i] < r_low and closes[i] > r_low
        bullish_fvg = lows[i] > highs[i-2]
        bearish_fvg = highs[i] < lows[i-2]

        # LONG
        if ((not htf_filter) or htf_trend in ["BULLISH", "NEUTRAL"]) and (is_sweep_low or (bullish_fvg and closes[i] > closes[i-1])):
            entry_price = closes[i]
            sl_price = lows[i-2:i+1].min() * 0.998
            risk = entry_price - sl_price
            if risk > 0:
                trade_signals.append({
                    'Time_SLST': t_time.strftime('%Y-%m-%d %I:%M %p'),
                    'Type': 'LONG', 'Entry': entry_price, 'SL': sl_price, 'TP1': entry_price + (risk * rr_ratio),
                    'Signal_ID': f"{symbol_name}_LONG_{t_time.strftime('%Y%m%d%H%M')}"
                })

        # SHORT
        if ((not htf_filter) or htf_trend in ["BEARISH", "NEUTRAL"]) and (is_sweep_high or (bearish_fvg and closes[i] < closes[i-1])):
            entry_price = closes[i]
            sl_price = highs[i-2:i+1].max() * 1.002
            risk = sl_price - entry_price
            if risk > 0:
                trade_signals.append({
                    'Time_SLST': t_time.strftime('%Y-%m-%d %I:%M %p'),
                    'Type': 'SHORT', 'Entry': entry_price, 'SL': sl_price, 'TP1': entry_price - (risk * rr_ratio),
                    'Signal_ID': f"{symbol_name}_SHORT_{t_time.strftime('%Y%m%d%H%M')}"
                })
    return df, trade_signals

# --- 🚀 BACKGROUND MULTI-COIN TELEGRAM SCANNER ---
if st.session_state.telegram_enabled and st.session_state.saved_telegram_token and st.session_state.saved_telegram_chat_id:
    for coin_to_scan in st.session_state.selected_tg_coins:
        c_raw = fetch_futures_data(coin_to_scan, execution_tf, limit=100)
        c_htf = fetch_futures_data(coin_to_scan, htf_tf, limit=50)
        if not c_raw.empty and not c_htf.empty:
            c_bias = calculate_htf_trend(c_htf)
            c_clean_name = coin_to_scan.replace("-SWAP", "").replace("-", "/")
            _, c_signals = process_ipda_engine_v3(c_raw, c_bias, risk_reward_target, use_session_filter, use_htf_filter, c_clean_name)
            
            if c_signals:
                last_sig = c_signals[-1]
                # Check if this signal is new (last candle signal) and not sent before
                if last_sig['Signal_ID'] not in st.session_state.sent_signals:
                    msg = (
                        f"🚨 *IPDA SIGNAL ALERT*\n\n"
                        f"*Coin:* `{c_clean_name}` ({last_sig['Type']})\n"
                        f"*Entry:* `${last_sig['Entry']:.4f}`\n"
                        f"*TP:* `${last_sig['TP1']:.4f}`\n"
                        f"*SL:* `${last_sig['SL']:.4f}`"
                    )
                    send_telegram_alert(st.session_state.saved_telegram_token, st.session_state.saved_telegram_chat_id, msg)
                    st.session_state.sent_signals.add(last_sig['Signal_ID'])

# --- MAIN DASHBOARD DISPLAY ---
st.title("🎯 IPDA Pro Master Entry Engine")

raw_df = fetch_futures_data(selected_coin, execution_tf, limit=limit)
htf_df = fetch_futures_data(selected_coin, htf_tf, limit=100)
clean_symbol_name = selected_coin.replace("-SWAP", "").replace("-", "/")

if not raw_df.empty and not htf_df.empty:
    htf_bias = calculate_htf_trend(htf_df)
    processed_df, signals_list = process_ipda_engine_v3(raw_df, htf_bias, risk_reward_target, use_session_filter, use_htf_filter, clean_symbol_name)
    current_price = processed_df['Close'].iloc[-1]

    st.metric("Live Price", f"${current_price:.4f}", delta=f"4H HTF Trend: {htf_bias}")

    latest_trade = signals_list[-1] if signals_list else None
    if latest_trade:
        st.subheader("⚡ Active Selected Pair Signal")
        st.write(latest_trade)

    # Chart
    fig = go.Figure(data=[go.Candlestick(x=processed_df.index, open=processed_df['Open'], high=processed_df['High'], low=processed_df['Low'], close=processed_df['Close'])])
    fig.update_layout(xaxis_rangeslider_visible=False, height=450, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
