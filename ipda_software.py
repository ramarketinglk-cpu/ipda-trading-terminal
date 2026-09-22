import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG & LAYOUT ---
st.set_page_config(
    page_title="IPDA Master Entry",
    page_icon="🎯",
    layout="wide"
)

# Auto Refresh Every 300 Seconds
st_autorefresh(interval=300 * 1000, key="ipda_auto_refresh")

# --- 0. SAAS LICENSE KEY & SUBSCRIPTION DATABASE ---
VALID_LICENSES = {
    # Key Name                     Plan Type        Expiration Date (YYYY-MM-DD)
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

# --- SIDEBAR LICENSE VERIFICATION ---
st.sidebar.header("🔑 Membership & License Auth")
input_license_key = st.sidebar.text_input("Enter License Key", type="password", help=" WhatsApp us for Lisence key +94750511732 ")

if not input_license_key:
    st.title("🏛️ IPDA Pro Master Entry)")
    st.info("🔒 Please enter a valid License Key in the sidebar to access the Trading Engine.")
    st.markdown(
        """
        ---
        ### 💡 How to get a License Key?
        To access the **IPDA Institutional Perpetual Futures Engine**, subscribe to a Monthly or Lifetime plan:
        - **Monthly Subscription:** $5 / month
        - **Lifetime Pass:** $25 one-time
        
        *Contact +94750511732 or visit our Telegram @mr_dilan to activate your key.*
        """
    )
    st.stop()

is_valid, plan_type, owner_name, exp_date, days_remaining, status_code = verify_license_key(input_license_key)

if not is_valid:
    if status_code == "EXPIRED":
        st.sidebar.error(f"❌ License Expired on {exp_date}!")
        st.error("⛔ Your subscription license key has EXPIRED. Please renew your membership to regain access.")
    else:
        st.sidebar.error("❌ Invalid License Key!")
        st.error("⛔ Invalid License Key provided. Please check your credentials or purchase a valid subscription.")
    st.stop()

# License Success Status Card in Sidebar
st.sidebar.success(f"✅ Active: {plan_type}")
st.sidebar.caption(f"👤 Owner: **{owner_name}**")
if plan_type == "LIFETIME":
    st.sidebar.caption("♾️ Validity: **Lifetime Access**")
else:
    st.sidebar.caption(f"📅 Expiry: **{exp_date}** ({days_remaining} days left)")

st.sidebar.markdown("---")

# --- MAIN ENGINE APP (RUNS ONLY IF LICENSE IS VALID) ---
st.title("🏛️ IPDA Pro SaaS Terminal Engine")
st.caption(f"Authenticated User: {owner_name} • Plan: {plan_type} • SLST Timezone (UTC+5:30)")

# --- TOP 50 PERPETUAL PAIRS (OKX API STANDARDS) ---
TOP_50_COINS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "BNB-USDT-SWAP", "XRP-USDT-SWAP",
    "DOGE-USDT-SWAP", "ADA-USDT-SWAP", "AVAX-USDT-SWAP", "LINK-USDT-SWAP", "SUI-USDT-SWAP",
    "NEAR-USDT-SWAP", "PEPE-USDT-SWAP", "APT-USDT-SWAP", "FET-USDT-SWAP", "LTC-USDT-SWAP",
    "DOT-USDT-SWAP", "SHIB-USDT-SWAP", "WIF-USDT-SWAP", "RENDER-USDT-SWAP", "TAO-USDT-SWAP",
    "ARB-USDT-SWAP", "OP-USDT-SWAP", "TIA-USDT-SWAP", "INJ-USDT-SWAP", "STX-USDT-SWAP",
    "ORDI-USDT-SWAP", "FIL-USDT-SWAP", "FLOKI-USDT-SWAP", "BONK-USDT-SWAP", "SEI-USDT-SWAP",
    "AAVE-USDT-SWAP", "RUNE-USDT-SWAP", "PENDLE-USDT-SWAP", "ARKM-USDT-SWAP", "WLD-USDT-SWAP",
    "ENA-USDT-SWAP", "NOT-USDT-SWAP", "JUP-USDT-SWAP", "ONDO-USDT-SWAP", "GALA-USDT-SWAP",
    "TRX-USDT-SWAP", "BCH-USDT-SWAP", "MATIC-USDT-SWAP", "ETC-USDT-SWAP", "ATOM-USDT-SWAP",
    "FTM-USDT-SWAP", "ALGO-USDT-SWAP", "KAS-USDT-SWAP"
]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎯 Pair & Strategy Settings")
selected_coin = st.sidebar.selectbox("Select Perpetual Pair", TOP_50_COINS, index=0)
execution_tf = st.sidebar.selectbox("Execution Timeframe", ["5m", "15m", "1h"], index=1)
htf_tf = "4h"

limit = st.sidebar.slider("Historical Candles Limit", min_value=100, max_value=1000, value=300)
risk_reward_target = st.sidebar.slider("Min Risk-to-Reward Ratio (RR)", 1.5, 5.0, 2.0, 0.5)

use_session_filter = st.sidebar.checkbox("Apply Session Kill Zone Filter (London/NY)", value=True)
use_htf_filter = st.sidebar.checkbox("Apply 4H HTF Trend Alignment Filter", value=True)

# --- RISK MANAGEMENT CALCULATOR INPUTS ---
st.sidebar.markdown("---")
st.sidebar.header("💰 Risk Management Inputs")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=10.0, value=1000.0, step=50.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
user_leverage = st.sidebar.number_input("Leverage (x)", min_value=1, max_value=125, value=10, step=1)

# --- TELEGRAM BOT CONFIGURATION ---
st.sidebar.markdown("---")
st.sidebar.header("📲 Telegram Bot Settings")
enable_telegram = st.sidebar.checkbox("Enable Telegram Alerts", value=False)
telegram_bot_token = st.sidebar.text_input("Bot Token", value="", type="password", help="BotFather මගින් ලැබෙන Bot Token එක ඇතුළත් කරන්න")
telegram_chat_id = st.sidebar.text_input("Chat ID", value="", help="ඔබේ Telegram User / Channel Chat ID එක ඇතුළත් කරන්න")

# State tracking for Sent Signals to prevent duplicates
if 'sent_signals' not in st.session_state:
    st.session_state.sent_signals = set()

# Function to Send Telegram Alert
def send_telegram_alert(token, chat_id, message):
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.sidebar.error(f"Telegram Alert Error: {e}")

# Map Timeframe to OKX API Interval Format
OKX_TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "1h": "1H",
    "4h": "4H"
}

# --- 1. DATA ENGINE (Cloud-Block Free Public Futures API Engine) ---
@st.cache_data(ttl=10)
def fetch_futures_data(inst_id, tf, limit=300):
    try:
        bar_tf = OKX_TF_MAP.get(tf, "15m")
        url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar_tf}&limit={limit}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            st.error(f"API HTTP Error [{res.status_code}] for {inst_id}")
            return pd.DataFrame()

        json_data = res.json()
        if json_data.get('code') != '0':
            st.error(f"API Error: {json_data.get('msg')}")
            return pd.DataFrame()

        raw_list = json_data.get('data', [])
        if not raw_list:
            return pd.DataFrame()

        # OKX returns candles: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        df = pd.DataFrame(raw_list, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'VolCcy', 'VolCcyQuote', 'Confirm'])
        df = df.iloc[::-1].reset_index(drop=True)  # Reverse to chronological order
        
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['Timestamp'] = pd.to_numeric(df['Timestamp'], errors='coerce')
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms', utc=True)
        df['Timestamp'] = df['Timestamp'].dt.tz_convert('Asia/Colombo')
        df.set_index('Timestamp', inplace=True)
        
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        st.error(f"Data Fetch Error for {inst_id}: {e}")
        return pd.DataFrame()

# --- 2. HTF TREND CALCULATOR ---
def calculate_htf_trend(df_htf):
    if df_htf.empty or len(df_htf) < 20:
        return "NEUTRAL"
    
    ema20 = df_htf['Close'].ewm(span=20, adjust=False).mean()
    last_close = df_htf['Close'].iloc[-1]
    last_ema = ema20.iloc[-1]

    if last_close > last_ema:
        return "BULLISH"
    elif last_close < last_ema:
        return "BEARISH"
    return "NEUTRAL"

# --- 3. SESSION FILTER (SLST TIME BASED) ---
def is_in_kill_zone(timestamp_slst):
    hour = timestamp_slst.hour
    minute = timestamp_slst.minute
    time_val = hour + (minute / 60.0)

    in_london = 12.5 <= time_val <= 15.5
    in_ny = 17.5 <= time_val <= 20.5
    return in_london or in_ny

# --- 4. POSITION SIZE CALCULATOR HELPER ---
def calculate_position_size(balance, risk_pct, entry, sl, leverage):
    risk_amount = balance * (risk_pct / 100.0)
    price_risk_pct = abs(entry - sl) / entry
    
    if price_risk_pct == 0:
        return 0, 0, 0, 0

    position_notional_usd = risk_amount / price_risk_pct
    coin_quantity = position_notional_usd / entry
    required_margin_usd = position_notional_usd / leverage

    return risk_amount, position_notional_usd, coin_quantity, required_margin_usd

# --- 5. UPGRADED IPDA ENGINE WITH SLST & RISK METRICS ---
def process_ipda_engine_v3(df, htf_trend, rr_ratio, session_filter, htf_filter, balance, risk_pct, leverage, symbol_name):
    if df.empty or len(df) < 30:
        return df, [], {}

    df['FVG_Bullish'] = False
    df['FVG_Bearish'] = False
    df['Sweep_High'] = False
    df['Sweep_Low'] = False
    df['Signal'] = "NEUTRAL"
    
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values

    trade_signals = []

    for i in range(20, len(df) - 5):
        current_time_slst = df.index[i]
        
        if session_filter and not is_in_kill_zone(current_time_slst):
            continue

        recent_high = np.max(highs[i-20:i])
        recent_low = np.min(lows[i-20:i])

        is_sweep_high = highs[i] > recent_high and closes[i] < recent_high
        is_sweep_low = lows[i] < recent_low and closes[i] > recent_low

        df.iloc[i, df.columns.get_loc('Sweep_High')] = is_sweep_high
        df.iloc[i, df.columns.get_loc('Sweep_Low')] = is_sweep_low

        bullish_fvg = lows[i] > highs[i-2]
        bearish_fvg = highs[i] < lows[i-2]

        df.iloc[i, df.columns.get_loc('FVG_Bullish')] = bullish_fvg
        df.iloc[i, df.columns.get_loc('FVG_Bearish')] = bearish_fvg

        # LONG SETUP
        allow_long = (not htf_filter) or (htf_filter and htf_trend in ["BULLISH", "NEUTRAL"])
        if allow_long and (is_sweep_low or (bullish_fvg and closes[i] > closes[i-1])):
            df.iloc[i, df.columns.get_loc('Signal')] = "LONG"
            entry_price = closes[i]
            sl_price = lows[i-2:i+1].min() * 0.998
            risk = entry_price - sl_price
            
            if risk > 0:
                tp1 = entry_price + (risk * rr_ratio)
                
                risk_amt, position_val, qty, margin = calculate_position_size(
                    balance, risk_pct, entry_price, sl_price, leverage
                )

                outcome = "PENDING"
                for j in range(i + 1, len(df)):
                    future_high = df['High'].iloc[j]
                    future_low = df['Low'].iloc[j]
                    
                    if future_low <= sl_price:
                        outcome = "LOSS (SL Hit)"
                        break
                    elif future_high >= tp1:
                        outcome = "WIN (TP Hit)"
                        break

                trade_signals.append({
                    'Time_SLST': current_time_slst.strftime('%Y-%m-%d %I:%M:%S %p'),
                    'Type': 'LONG',
                    'Entry': entry_price,
                    'SL': sl_price,
                    'TP1': tp1,
                    'Outcome': outcome,
                    'Risk_USD': risk_amt,
                    'Position_USD': position_val,
                    'Qty': qty,
                    'Margin_USD': margin,
                    'Signal_ID': f"{symbol_name}_LONG_{current_time_slst.strftime('%Y%m%d%H%M')}"
                })

        # SHORT SETUP
        allow_short = (not htf_filter) or (htf_filter and htf_trend in ["BEARISH", "NEUTRAL"])
        if allow_short and (is_sweep_high or (bearish_fvg and closes[i] < closes[i-1])):
            df.iloc[i, df.columns.get_loc('Signal')] = "SHORT"
            entry_price = closes[i]
            sl_price = highs[i-2:i+1].max() * 1.002
            risk = sl_price - entry_price

            if risk > 0:
                tp1 = entry_price - (risk * rr_ratio)

                risk_amt, position_val, qty, margin = calculate_position_size(
                    balance, risk_pct, entry_price, sl_price, leverage
                )

                outcome = "PENDING"
                for j in range(i + 1, len(df)):
                    future_high = df['High'].iloc[j]
                    future_low = df['Low'].iloc[j]

                    if future_high >= sl_price:
                        outcome = "LOSS (SL Hit)"
                        break
                    elif future_low <= tp1:
                        outcome = "WIN (TP Hit)"
                        break

                trade_signals.append({
                    'Time_SLST': current_time_slst.strftime('%Y-%m-%d %I:%M:%S %p'),
                    'Type': 'SHORT',
                    'Entry': entry_price,
                    'SL': sl_price,
                    'TP1': tp1,
                    'Outcome': outcome,
                    'Risk_USD': risk_amt,
                    'Position_USD': position_val,
                    'Qty': qty,
                    'Margin_USD': margin,
                    'Signal_ID': f"{symbol_name}_SHORT_{current_time_slst.strftime('%Y%m%d%H%M')}"
                })

    # Stats Calculation
    total_trades = len([t for t in trade_signals if t['Outcome'] != 'PENDING'])
    wins = len([t for t in trade_signals if "WIN" in t['Outcome']])
    losses = len([t for t in trade_signals if "LOSS" in t['Outcome']])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    stats = {
        'Total': total_trades,
        'Wins': wins,
        'Losses': losses,
        'WinRate': win_rate
    }

    return df, trade_signals, stats

# --- 6. EXECUTION & RENDERING ---
raw_df = fetch_futures_data(selected_coin, execution_tf, limit=limit)
htf_df = fetch_futures_data(selected_coin, htf_tf, limit=100)

clean_symbol_name = selected_coin.replace("-SWAP", "").replace("-", "/")

if not raw_df.empty and not htf_df.empty:
    htf_bias = calculate_htf_trend(htf_df)
    processed_df, signals_list, metrics = process_ipda_engine_v3(
        raw_df, htf_bias, risk_reward_target, use_session_filter, use_htf_filter,
        account_balance, risk_percentage, user_leverage, clean_symbol_name
    )
    current_price = processed_df['Close'].iloc[-1]

    # TOP STATS CARDS
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Live Price", f"${current_price:.4f}")
    s2.metric("4H HTF Trend Filter", f"{htf_bias}")
    s3.metric("Filtered Trades", f"{metrics.get('Total', 0)}")
    s4.metric("Wins / Losses", f"{metrics.get('Wins', 0)} / {metrics.get('Losses', 0)}")
    
    wr = metrics.get('WinRate', 0.0)
    wr_color = "normal" if wr >= 50 else "inverse"
    s5.metric("High-Probability Win Rate", f"{wr:.1f}%", delta=f"{wr - 40.0:.1f}% vs Default", delta_color=wr_color)

    st.markdown("---")

    # LATEST ACTIVE TRADE SETUP & TELEGRAM TRIGGER
    latest_trade = signals_list[-1] if signals_list else None

    if latest_trade:
        st.subheader("⚡ Active Signal Setup")
        c_type = latest_trade['Type']
        box_color = "rgba(0, 230, 118, 0.1)" if c_type == "LONG" else "rgba(255, 82, 82, 0.1)"
        border_color = "#00E676" if c_type == "LONG" else "#FF5252"

        st.markdown(
            f"""
            <div style="background-color: {box_color}; padding: 15px; border-radius: 10px; border-left: 6px solid {border_color};">
                <h3 style="margin:0; color: {border_color};">{c_type} SIGNAL ({clean_symbol_name})</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.8;">Generated at {latest_trade['Time_SLST']} (SLST)</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.write("")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📍 ENTRY LEVEL", f"${latest_trade['Entry']:.4f}")
        p2.metric("🛑 STOP LOSS (SL)", f"${latest_trade['SL']:.4f}")
        p3.metric("🎯 TAKE PROFIT (TP1)", f"${latest_trade['TP1']:.4f}")
        p4.metric("📌 OUTCOME STATUS", f"{latest_trade['Outcome']}")

        # POSITION SIZE METRICS DISPLAY
        st.markdown("##### 🧮 Futures Position Sizing Breakdown")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Max Dollar Risk ($)", f"${latest_trade['Risk_USD']:.2f}")
        r2.metric("Exact Order Qty (Coins)", f"{latest_trade['Qty']:.4f}")
        r3.metric("Position Size (Notional $)", f"${latest_trade['Position_USD']:.2f}")
        r4.metric("Required Margin ($)", f"${latest_trade['Margin_USD']:.2f}")

        # --- TELEGRAM BOT SIGNAL DISPATCHER ---
        if enable_telegram and latest_trade['Signal_ID'] not in st.session_state.sent_signals:
            emoji = "🟢" if c_type == "LONG" else "🔴"
            msg = (
                f"🚨 *NEW IPDA SIGNAL ALERT* 🚨\n\n"
                f"*Pair:* `{clean_symbol_name}` PERP\n"
                f"*Signal:* {emoji} *{c_type}*\n"
                f"*Time:* `{latest_trade['Time_SLST']}` (SLST)\n\n"
                f"📍 *Entry:* `${latest_trade['Entry']:.4f}`\n"
                f"🛑 *Stop Loss:* `${latest_trade['SL']:.4f}`\n"
                f"🎯 *Take Profit 1:* `${latest_trade['TP1']:.4f}`\n\n"
                f"🧮 *POSITION SIZING ({user_leverage}x Leverage):*\n"
                f"• *Order Qty:* `{latest_trade['Qty']:.4f}` Coins\n"
                f"• *Max Dollar Risk:* `${latest_trade['Risk_USD']:.2f}`\n"
                f"• *Required Margin:* `${latest_trade['Margin_USD']:.2f}`\n\n"
                f"🏛️ _IPDA Institutional Engine_"
            )
            send_telegram_alert(telegram_bot_token, telegram_chat_id, msg)
            st.session_state.sent_signals.add(latest_trade['Signal_ID'])
            st.toast(f"Telegram Alert Sent for {clean_symbol_name} {c_type}!", icon="📲")

    st.markdown("---")

    # CHART
    st.subheader(f"📊 {clean_symbol_name} Execution Chart ({execution_tf} - SLST)")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=processed_df.index,
        open=processed_df['Open'],
        high=processed_df['High'],
        low=processed_df['Low'],
        close=processed_df['Close'],
        name="Price"
    ))

    if latest_trade:
        fig.add_hline(y=latest_trade['Entry'], line_dash="solid", line_color="#29B6F6", annotation_text="ENTRY")
        fig.add_hline(y=latest_trade['SL'], line_dash="dash", line_color="#FF5252", annotation_text="SL")
        fig.add_hline(y=latest_trade['TP1'], line_dash="dot", line_color="#00E676", annotation_text="TP1")

    fig.update_layout(xaxis_rangeslider_visible=False, height=520, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # HISTORY LOG WITH SLST TIMESTAMP
    st.subheader("📋 Filtered Signals History & Position Metrics Log (SLST)")
    if signals_list:
        sig_df = pd.DataFrame(signals_list)
        st.dataframe(
            sig_df[['Time_SLST', 'Type', 'Entry', 'SL', 'TP1', 'Outcome', 'Risk_USD', 'Qty', 'Position_USD', 'Margin_USD']].sort_values(by='Time_SLST', ascending=False),
            use_container_width=True
        )
    else:
        st.info(f"No high-probability signals matched the strict session and HTF filters for {clean_symbol_name} in this range.")

else:
    st.warning(f"Connecting to Futures API for {clean_symbol_name}...")
