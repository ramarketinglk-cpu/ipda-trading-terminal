import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG & LAYOUT ---
st.set_page_config(
    page_title="IPDA Pro Terminal & Telegram Bot",
    page_icon="🏛️",
    layout="wide"
)

# Auto Refresh Every 300 Seconds
st_autorefresh(interval=300 * 1000, key="ipda_auto_refresh")

st.title("🏛️ IPDA Pro Terminal & Telegram Alert Engine")
st.caption("Binance Futures Risk Management • SLST Timezone (UTC+5:30) • Instant Telegram Signals")

# --- TOP 50 BINANCE PERPETUAL COINS LIST ---
TOP_50_COINS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "SUI/USDT",
    "NEAR/USDT", "PEPE/USDT", "APT/USDT", "FET/USDT", "LTC/USDT",
    "DOT/USDT", "SHIB/USDT", "WIF/USDT", "RENDER/USDT", "TAO/USDT",
    "ARBITRUM/USDT", "OP/USDT", "TIA/USDT", "INJ/USDT", "STX/USDT",
    "ORDI/USDT", "FIL/USDT", "FLOKI/USDT", "BONK/USDT", "SEI/USDT",
    "AAVE/USDT", "RUNE/USDT", "PENDLE/USDT", "ARKM/USDT", "WLD/USDT",
    "ENA/USDT", "NOT/USDT", "JUP/USDT", "ONDO/USDT", "GALA/USDT",
    "TRX/USDT", "BCH/USDT", "MATIC/USDT", "ETC/USDT", "ATOM/USDT",
    "FTM/USDT", "ALGO/USDT", "KAS/USDT"
]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎯 Pair & Strategy Settings")
symbol = st.sidebar.selectbox("Select Binance Pair", TOP_50_COINS, index=0)
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

# --- 1. DATA ENGINE (Binance API with SLST Timezone Conversion) ---
@st.cache_data(ttl=10)
def fetch_futures_data(symbol_name, tf, limit=300):
    try:
        exchange = ccxt.binance({
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        ohlcv = exchange.fetch_ohlcv(symbol_name, timeframe=tf, limit=limit)
        if not ohlcv:
            return pd.DataFrame()
            
        df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms', utc=True)
        df['Timestamp'] = df['Timestamp'].dt.tz_convert('Asia/Colombo')
        df.set_index('Timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"Binance Data Fetch Error for {symbol_name}: {e}")
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
raw_df = fetch_futures_data(symbol, execution_tf, limit=limit)
htf_df = fetch_futures_data(symbol, htf_tf, limit=100)

if not raw_df.empty and not htf_df.empty:
    htf_bias = calculate_htf_trend(htf_df)
    processed_df, signals_list, metrics = process_ipda_engine_v3(
        raw_df, htf_bias, risk_reward_target, use_session_filter, use_htf_filter,
        account_balance, risk_percentage, user_leverage, symbol
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
        st.subheader("⚡ Active Signal Setup (SLST Timezone)")
        c_type = latest_trade['Type']
        box_color = "rgba(0, 230, 118, 0.1)" if c_type == "LONG" else "rgba(255, 82, 82, 0.1)"
        border_color = "#00E676" if c_type == "LONG" else "#FF5252"

        st.markdown(
            f"""
            <div style="background-color: {box_color}; padding: 15px; border-radius: 10px; border-left: 6px solid {border_color};">
                <h3 style="margin:0; color: {border_color};">{c_type} SIGNAL ({symbol})</h3>
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
        st.markdown("##### 🧮 Binance Futures Position Sizing Breakdown")
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
                f"*Pair:* `{symbol}` PERP\n"
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
            st.toast(f"Telegram Alert Sent for {symbol} {c_type}!", icon="📲")

    st.markdown("---")

    # CHART
    st.subheader(f"📊 {symbol} Execution Chart ({execution_tf} - SLST)")

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
        st.info(f"No high-probability signals matched the strict session and HTF filters for {symbol} in this range.")

else:
    st.warning(f"Connecting to Binance Futures API for {symbol}...")