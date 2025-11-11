import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from fastapi import Header, HTTPException

@app.get("/api/v1/signals")
def get_signals(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    now = datetime.now(timezone.utc)
    output = []
    pairs = {
        "XAU/USD": "Gold",
        "EUR/USD": "EUR/USD",
        "GBP/USD": "GBP/USD",
        "USD/JPY": "USD/JPY",
        "BTC/USD": "Bitcoin"
    }

    for symbol, name in pairs.items():
        try:
            # --- Fetch from Twelve Data ---
            api_key_td = os.getenv("TWELVEDATA_API_KEY", "")
            url = f"https://api.twelvedata.com/price?symbol={symbol.replace('/', '')}&apikey={api_key_td}"
            res = requests.get(url, timeout=10)
            data = res.json()
            print(f"🔍 {symbol} API response:", data)

            # --- Parse price ---
            if "price" in data:
                price = float(data["price"])
            else:
                # fallback: Yahoo Finance
                df = yf.download(symbol.replace('/', '') + "=X", period="1d", interval="5m", progress=False)
                if df.empty:
                    print(f"⚠️ No data for {symbol}")
                    continue
                price = float(df["Close"].iloc[-1])

            # --- Compute a simple trend signal ---
            df_temp = pd.DataFrame({"Close": [price * 0.999, price]})
            sig, conf = compute_signal(df_temp)

            output.append({
                "symbol": symbol,
                "name": name,
                "signal": sig,
                "confidence": conf,
                "price": round(price, 4),
                "timestamp": now.isoformat()
            })
            print(f"✅ {symbol}: {price}")

        except Exception as e:
            print(f"⚠️ Error fetching {symbol}: {e}")

    if not output:
        return {"status": "initializing", "message": "Cache warming up"}

    _cache["signals"] = output
    _cache["timestamp"] = now
    return output
