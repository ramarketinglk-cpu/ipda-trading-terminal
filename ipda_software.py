import requests
import time

# --- ඔයාගේ Telegram දත්ත ---
TELEGRAM_TOKEN = "8931894026:AAGeHxiEtzwXQ7Mvjcf7S0wz-duNgZkPYJQ"
CHAT_ID = "5472603423"

def send_telegram_message(message):
    """Telegram Bot හරහා Message එක යැවීමේ Function එක"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" 
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_market_data():
    """Binance එකෙන් මේ මොහොතේ Market Data එක ගන්නවා"""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error connecting to Binance: {e}")
        return None

def find_early_pumps():
    print("Early Pump Detector with Telegram Alerts Started...\n")
    print("Waiting for the first 60 seconds to gather baseline data...\n")
    
    previous_data = {}

    while True:
        current_data = get_market_data()
        
        if not current_data:
            time.sleep(10)
            continue

        spiking_coins = []
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')

        for coin in current_data:
            symbol = coin['symbol']
            
            # USDT pairs පමණක් තෝරන්න
            if symbol.endswith('USDT') and not any(sb in symbol for sb in ['USDC', 'FDUSD', 'TUSD', 'DAI']):
                current_price = float(coin['lastPrice'])
                current_volume = float(coin['quoteVolume'])

                if symbol in previous_data:
                    prev_price = previous_data[symbol]['price']
                    prev_volume = previous_data[symbol]['volume']

                    price_change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
                    volume_traded_in_60s = current_volume - prev_volume

                    # --- EARLY SIGNAL STRATEGY ---
                    if 0.5 <= price_change_pct <= 3.0 and volume_traded_in_60s >= 50000:
                        spiking_coins.append({
                            'symbol': symbol,
                            'price': current_price,
                            'price_change_60s': price_change_pct,
                            'new_volume': volume_traded_in_60s
                        })

                previous_data[symbol] = {
                    'price': current_price,
                    'volume': current_volume
                }
        
        spiking_coins = sorted(spiking_coins, key=lambda x: x['new_volume'], reverse=True)

        print(f"================ Scan Time: {current_time} ================")
        
        if spiking_coins:
            print("EARLY PUMP SIGNALS DETECTED! Sending to Telegram...")
            
            tg_message = "*EARLY PUMP ALERT*\n\n"
            
            for item in spiking_coins[:5]:
                tg_message += f"Coin: {item['symbol']}\n"
                tg_message += f"Price: ${item['price']:.6f}\n"
                tg_message += f"Moved: +{item['price_change_60s']:.2f} percent\n"
                tg_message += f"New Volume: ${item['new_volume']:,.0f}\n\n"
                
                # ගැටළුව ආපු තැන සරල කර ඇත
                print(f"Coin: {item['symbol']} -- Price: ${item['price']:.4f} -- Moved: {item['price_change_60s']:.2f} percent -- New Vol: ${item['new_volume']:,.0f}")
            
            send_telegram_message(tg_message)
            
        else:
            print("No early signals found. Market is quiet.")
            
        print("\nGathering data... Next scan in 60 seconds...\n")
        time.sleep(60)

# Bot එක Run කිරීම
find_early_pumps()
