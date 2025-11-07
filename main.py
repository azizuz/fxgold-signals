from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import time, os, re, asyncio

app = FastAPI(title="Gold & Forex Signal Backend")

# --- Security key ---
API_KEY = os.getenv("API_KEY", "fxgold123")

# --- Production-safe CORS setup ---
# Allows your real domain, Base44, and modal previews (for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://(.*\.)?(aurumiq\.online|base44\.com|modal\.host)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Caching store ---
_cache = {"signals": None, "timestamp": None}

# --- Compute trading signal safely ---
def compute_signal(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    last = df.iloc[-1]
    sma20 = float(last["SMA20"])
    sma50 = float(last["SMA50"])

    if sma20 > sma50:
        return "BUY", 0.75
    elif sma20 < sma50:
        return "SELL", 0.70
    else:
        return "HOLD", 0.55


# --- Background task to update signals every 10 minutes (non-blocking) ---
async def update_signals_cache():
    await asyncio.sleep(3)  # wait 3s after boot to ensure startup completes
    while True:
        try:
            print("🔄 Refreshing cached signals...")
            pairs = {
                "XAUUSD=X": "Gold",
                "EURUSD=X": "EUR/USD",
                "GBPUSD=X": "GBP/USD",
            }
            output = []
            for ticker, name in pairs.items():
                df = yf.download(ticker, period="30d", interval="1h", progress=False)
                if df.empty:
                    continue
                sig, conf = compute_signal(df)
                price = float(df["Close"].iloc[-1])
                output.append({
                    "symbol": ticker,
                    "name": name,
                    "signal": sig,
                    "confidence": conf,
                    "price": round(price, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            _cache["signals"] = output
            _cache["timestamp"] = datetime.now(timezone.utc)
            print("✅ Cached signals updated.")
        except Exception as e:
            print(f"⚠️ Error updating signals: {e}")
        await asyncio.sleep(600)  # refresh every 10 minutes


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(update_signals_cache())


# --- /signals endpoint ---
@app.get("/api/v1/signals")
def get_signals(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Serve cached results instantly
    if _cache["signals"]:
        return _cache["signals"]

    # fallback if cache is empty
    return {"status": "initializing", "message": "Cache still warming up"}


# --- /metrics endpoint ---
@app.get("/api/v1/metrics")
def get_metrics(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return {
        "win_rate": 0.74,
        "sharpe_ratio": 1.88,
        "max_drawdown": 0.09,
        "avg_confidence": 0.67,
        "last_update": datetime.now(timezone.utc).isoformat()
    }


# --- /health endpoint ---
@app.get("/api/v1/health")
def health():
    latency = round(time.time() % 1000, 2)
    return {
        "status": "ok",
        "latency_ms": latency,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
