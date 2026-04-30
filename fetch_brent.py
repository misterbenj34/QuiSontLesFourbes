import requests
import json
import time
import datetime
import os

OUTPUT_FILE = "brent_prices.json"

def fetch_brent_prices():
    # Depuis le 1er janvier 2026
    start_date = int(datetime.datetime(2026, 1, 1).timestamp())
    end_date = int(time.time())

    # Ticker pour le Brent Crude Oil Futures sur Yahoo Finance
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/BZ=F?period1={start_date}&period2={end_date}&interval=1d"
    # Yahoo Finance requiert un User-Agent valide
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        timestamps = data['chart']['result'][0]['timestamp']
        close_prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
        
        # Load existing data to merge
        history = {}
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r') as f:
                try:
                    history = json.load(f)
                except:
                    pass

        count = 0
        for ts, price in zip(timestamps, close_prices):
            if price is not None:
                # Yahoo Finance timestamps are usually around market close
                date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                history[date_str] = {
                    "price_usd": round(price, 2)
                }
                count += 1
                
        # Sort by date and save
        sorted_history = dict(sorted(history.items()))
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(sorted_history, f, indent=2)
            
        print(f"Succès : {count} jours de prix du baril de Brent récupérés.")
        
    except Exception as e:
        print(f"Erreur lors de la récupération des prix du baril : {e}")

if __name__ == "__main__":
    fetch_brent_prices()
