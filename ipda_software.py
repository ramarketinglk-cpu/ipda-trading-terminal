import time
import requests
import streamlit as st

# Streamlit Page Config
st.set_page_config(
    page_title="Crypto Early Pump Detector", page_icon="🚀", layout="centered"
)

st.title("🚀 Crypto Early Pump Detector with Telegram Alerts")
st.markdown(
    "මෙම ඇප් එක මගින් Binance වෙළඳපොළ නිරීක්ෂණය කර, හදිසි මිල ඉහළ යාම් (Pumps) හඳුනාගෙන Telegram වෙත පණිවිඩ එවයි."
)

# Sidebar - Settings / Credentials
st.sidebar.header("⚙️ Settings")
TELEGRAM_TOKEN = st.sidebar.text_input(
    "Telegram Token",
    value="8931894026:AAGeHxiEtzwXQ7Mvjcf7S0wz-duNgZkPYJQ",
    type="password",
)
CHAT_ID = st.sidebar.text_input("Chat ID", value="5472603423")

# Control Buttons
st.sidebar.markdown("---")
if "running" not in st.session_state:
    st.session_state.running = False

col1, col2 = st.sidebar.columns(2)
if col1:
    start_btn = col1.button("Start Bot")
if col2:
    stop_btn = col2.button("Stop Bot")

if start_btn:
    st.session_state.running = True
if stop_btn:
    st.session_state.running = False


def send_telegram_message(message, token, chat_id):
  """Telegram Bot හරහා Message එක යැවීමේ Function එක"""
  if not token or not chat_id:
    return
  url = f"https://api.telegram.org/bot{token}/sendMessage"
  payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload)
  except Exception as e:
    st.error(f"Error sending Telegram message: {e}")


def get_market_data():
  """Binance එකෙන් මේ මොහොතේ Market Data එක ගන්නවා"""
  url = "https://api.binance.com/api/v3/ticker/24hr"
  try:
    response = requests.get(url)
    return response.json()
  except Exception as e:
    st.error(f"Error connecting to Binance: {e}")
    return None


# Main Container for live logs/results
log_container = st.container()
status_placeholder = st.empty()

# Bot Loop Logic
if st.session_state.running:
  status_placeholder.success(
      "🟢 Bot එක ක්‍රියාත්මක වෙමින් පවතී (Running)..."
  )

  # Initial baseline data gather
  with log_container:
    st.info("Waiting for the first 60 seconds to gather baseline data...")

  previous_data = {}

  # Initial data fetch
  current_data = get_market_data()
  if current_data:
    for coin in current_data:
      symbol = coin["symbol"]
      if symbol.endswith("USDT") and not any(
          sb in symbol for sb in ["USDC", "FDUSD", "TUSD", "DAI"]
      ):
        previous_data[symbol] = {
            "price": float(coin["lastPrice"]),
            "volume": float(coin["quoteVolume"]),
        }

  time.sleep(10)  # Short pause before entering real loop

  # Streamlit loop
  while st.session_state.running:
    current_data = get_market_data()

    if not current_data:
      time.sleep(10)
      continue

    spiking_coins = []
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    for coin in current_data:
      symbol = coin["symbol"]

      if symbol.endswith("USDT") and not any(
          sb in symbol for sb in ["USDC", "FDUSD", "TUSD", "DAI"]
      ):
        try:
          current_price = float(coin["lastPrice"])
          current_volume = float(coin["quoteVolume"])
        except ValueError:
          continue

        if symbol in previous_data:
          prev_price = previous_data[symbol]["price"]
          prev_volume = previous_data[symbol]["volume"]

          price_change_pct = (
              ((current_price - prev_price) / prev_price) * 100
              if prev_price > 0
              else 0
          )
          volume_traded_in_60s = current_volume - prev_volume

          # --- EARLY SIGNAL STRATEGY ---
          if 0.5 <= price_change_pct <= 3.0 and volume_traded_in_60s >= 50000:
            spiking_coins.append({
                "symbol": symbol,
                "price": current_price,
                "price_change_60s": price_change_pct,
                "new_volume": volume_traded_in_60s,
            })

        previous_data[symbol] = {"price": current_price, "volume": current_volume}

    spiking_coins = sorted(
        spiking_coins, key=lambda x: x["new_volume"], reverse=True
    )

    with log_container:
      st.write(f"--- **Scan Time:** {current_time} ---")

      if spiking_coins:
        st.warning("🔥 EARLY PUMP SIGNALS DETECTED! Sending to Telegram...")
        tg_message = "*EARLY PUMP ALERT*\n\n"

        for item in spiking_coins[:5]:
          tg_message += f"Coin: {item['symbol']}\n"
          tg_message += f"Price: ${item['price']:.6f}\n"
          tg_message += f"Moved: +{item['price_change_60s']:.2f} percent\n"
          tg_message += f"New Volume: ${item['new_volume']:,.0f}\n\n"

          st.write(
              f"✅ **{item['symbol']}** | Price: `${item['price']:.4f}` |"
              f" Moved: `+{item['price_change_60s']:.2f}%` | Vol:"
              f" `${item['new_volume']:,.0f}`"
          )

        send_telegram_message(tg_message, TELEGRAM_TOKEN, CHAT_ID)
      else:
        st.info("No early signals found. Market is quiet.")

    # Wait 60 seconds before next scan
    time.sleep(60)
    st.rerun()

else:
  status_placeholder.warning(
      "🔴 Bot එක නවතා ඇත. Start Bot බොත්තම ඔබන්න."
  )
