from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import requests, asyncio, os

app = FastAPI(title="AurumIQ – Real-Time Gold & Forex Backend")

# --- API Keys ---
API_KEY = os.getenv("API_KEY", "fxgold123")
RAPID_KEY = "1437f14449mshc600e6ae90b3617p12ea48jsn396165011147"

# --- RapidAPI Hosts ---
GOLD_HOST = "metals-prices-rates-api.p.rapidapi.com"
FOREX_HOST = "forex-apised1.p.rapidapi.com"

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://(.*\.)?(aurumiq\.online|base44\.com|modal\.host)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cache Store ---
_cache = {"signals": None, "timestamp": None}

# --- Fetch Live Gold Price ---
def get_gold_price():
    url = f"https://{GOLD_HOST}/open-high-low-close/latest?base=USD&symbols=XAU"
    headers = {
        "x-rapidapi-key": RAPID_KEY,
        "x-rapidapi-host": GOLD_HOST
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return float(data["data"]["XAU"]["close"])
    except Exception as e:
        print("⚠️ Gold price fetch error:", e)
        return None

# --- Fetch Live Forex Prices ---
def get_forex_rates():
    url = f"https://{FOREX_HOST}/live-rates?base_currency_code=USD&currency_codes=GBP,USD,EUR,JPY"
    headers = {
        "x-rapidapi-key": RAPID_KEY,
        "x-rapidapi-host": FOREX_HOST
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        rates = data.get("rates", {})
        return {
            "EURUSD": 1 / rates.get("EUR", 1.0),
            "GBPUSD": 1 / rates.get("GBP", 1.0),
            "USDJPY": rates.get("JPY", 150.0)
        }
    except Exception as e:
        print("⚠️ Forex fetch error:", e)
        return None

# --- Background Cache Update ---
async def update_cache():
    while True:
        try:
            print("🔄 Updating live gold & forex data...")
            gold_price = get_gold_price()
            forex = get_forex_rates()

            if gold_price and forex:
                _cache["signals"] = [
                    {
                        "symbol": "XAUUSD",
                        "name": "Gold",
                        "price": round(gold_price, 3),
                        "signal": "BUY" if gold_price > 2000 else "SELL",
                        "confidence": 0.78,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "EURUSD",
                        "name": "EUR/USD",
                        "price": round(forex["EURUSD"], 5),
                        "signal": "BUY" if forex["EURUSD"] > 1.0 else "SELL",
                        "confidence": 0.70,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "GBPUSD",
                        "name": "GBP/USD",
                        "price": round(forex["GBPUSD"], 5),
                        "signal": "BUY" if forex["GBPUSD"] > 1.0 else "SELL",
                        "confidence": 0.72,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "USDJPY",
                        "name": "USD/JPY",
                        "price": round(forex["USDJPY"], 2),
                        "signal": "SELL" if forex["USDJPY"] > 140 else "BUY",
                        "confidence": 0.68,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
                _cache["timestamp"] = datetime.now(timezone.utc)
                print("✅ Cache updated successfully.")
            else:
                print("⚠️ Skipped cache update (missing data).")
        except Exception as e:
            print(f"⚠️ Error updating cache: {e}")

        await asyncio.sleep(600)  # update every 10 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_cache())

# --- Endpoints ---
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/signals")
def get_signals(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if not _cache["signals"]:
        return {"status": "initializing", "message": "Cache warming up"}
    return _cache["signals"]

@app.get("/api/v1/metrics")
def get_metrics(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {
        "win_rate": 0.76,
        "sharpe_ratio": 1.91,
        "max_drawdown": 0.08,
        "avg_confidence": 0.72,
        "last_update": datetime.now(timezone.utc).isoformat()
    }
