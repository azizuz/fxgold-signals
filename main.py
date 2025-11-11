from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os, requests, pandas as pd, yfinance as yf

# --- Initialize app BEFORE endpoints ---
app = FastAPI(title="Gold & Forex Signal Backend")

# --- Security key ---
API_KEY = os.getenv("API_KEY", "fxgold123")

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://(.*\.)?(aurumiq\.online|base44\.com|modal\.host)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cache store ---
_cache = {"signals": None, "timestamp": None}

# --- Signal computation ---
def compute_signal(df):
    df["SMA20"] = df["Close"].rolling(2).mean()
    df["SMA50"] = df["Close"].rolling(2).mean()
    last = df.iloc[-1]
    if last["SMA20"] > last["SMA50"]:
        return "BUY", 0.75
    elif last["SMA20"] < last["SMA50"]:
        return "SELL", 0.70
    else:
        return "HOLD", 0.60

# ✅ --- /signals endpoint (paste your version here) ---
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
    }

    for symbol, name in pairs.items():
        try:
            api_key_td = os.getenv("TWELVEDATA_API_KEY", "")
            url = f"https://api.twelvedata.com/price?symbol={symbol.replace('/', '')}&apikey={api_key_td}"
            res = requests.get(url, timeout=10)
            data = res.json()
            print(f"🔍 {symbol} API response:", data)

            if "price" in data:
                price = float(data["price"])
            else:
                df = yf.download(symbol.replace('/', '') + "=X", period="1d", interval="5m", progress=False)
                if df.empty:
                    print(f"⚠️ No data for {symbol}")
                    continue
                price = float(df["Close"].iloc[-1])

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

# --- Other endpoints ---
@app.get("/api/v1/metrics")
def get_metrics(...):
    ...

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
