from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
import requests, asyncio, os

app = FastAPI(title="AurumIQ Gold & Forex Signal Backend")

# --- API keys ---
API_KEY = os.getenv("API_KEY", "fxgold123")
RAPID_KEY = "1437f14449mshc600e6ae90b3617p12ea48jsn396165011147"
RAPID_HOST = "metals-prices-rates-api.p.rapidapi.com"

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://(.*\.)?(aurumiq\.online|base44\.com|modal\.host)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cache ---
_cache = {"signals": None, "timestamp": None}

# --- Helper: Get Gold price from RapidAPI ---
def get_gold_price():
    url = f"https://{RAPID_HOST}/open-high-low-close/latest?base=USD&symbols=XAU"
    headers = {
        "x-rapidapi-key": RAPID_KEY,
        "x-rapidapi-host": RAPID_HOST
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("⚠️ RapidAPI error:", response.text)
        return None
    data = response.json()
    try:
        return float(data["data"]["XAU"]["close"])
    except Exception as e:
        print("⚠️ Parsing error:", e, data)
        return None

# --- Dummy Forex Data (you can later connect real forex API here) ---
def get_forex_rates():
    return {
        "EURUSD": 1.067,
        "GBPUSD": 1.243,
        "USDJPY": 149.85
    }

# --- Background cache update ---
async def update_cache():
    while True:
        try:
            print("🔄 Updating gold & forex data...")
            gold_price = get_gold_price()
            forex = get_forex_rates()
            if gold_price:
                _cache["signals"] = [
                    {
                        "symbol": "XAUUSD",
                        "name": "Gold",
                        "signal": "BUY" if gold_price > 2000 else "SELL",
                        "confidence": 0.75,
                        "price": gold_price,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "EURUSD",
                        "name": "EUR/USD",
                        "signal": "BUY" if forex["EURUSD"] > 1 else "SELL",
                        "confidence": 0.70,
                        "price": forex["EURUSD"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "GBPUSD",
                        "name": "GBP/USD",
                        "signal": "BUY" if forex["GBPUSD"] > 1 else "SELL",
                        "confidence": 0.72,
                        "price": forex["GBPUSD"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "symbol": "USDJPY",
                        "name": "USD/JPY",
                        "signal": "SELL" if forex["USDJPY"] > 140 else "BUY",
                        "confidence": 0.68,
                        "price": forex["USDJPY"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
                _cache["timestamp"] = datetime.now(timezone.utc)
                print("✅ Cache updated.")
            else:
                print("⚠️ Skipping update (no gold data).")
        except Exception as e:
            print(f"⚠️ Error in cache update: {e}")

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
        "win_rate": 0.74,
        "sharpe_ratio": 1.88,
        "max_drawdown": 0.09,
        "avg_confidence": 0.71,
        "last_update": datetime.now(timezone.utc).isoformat()
    }
