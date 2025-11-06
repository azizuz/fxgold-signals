from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import time, os

app = FastAPI(title="Gold & Forex Signal Backend")

API_KEY = os.getenv("API_KEY", "fxgold123")

origins = [
    "https://app.base44.com",        # Base44 main app
    "https://base44.com",            # Base44 API domain
    "https://fxgold-signals.onrender.com",  # your backend itself
    "https://aurum-iq-1fc1317b.base44.app"  # replace with YOUR Base44 app URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def compute_signal(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    last = df.iloc[-1]
    if last["SMA20"] > last["SMA50"]:
        return "BUY", 0.75
    elif last["SMA20"] < last["SMA50"]:
        return "SELL", 0.70
    else:
        return "HOLD", 0.55

@app.get("/api/v1/signals")
def get_signals(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    pairs = {"XAUUSD=X": "Gold", "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD"}
    output = []
    for ticker, name in pairs.items():
        df = yf.download(ticker, period="30d", interval="1h", progress=False)
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
    return output

@app.get("/api/v1/metrics")
def get_metrics(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return {
        "win_rate": 0.74,
        "sharpe_ratio": 1.88,
        "max_drawdown": 0.09,
        "avg_confidence": 0.67,
        "last_update": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/health")
def health():
    start = time.time()
    _ = yf.download("XAUUSD=X", period="1d", interval="1h", progress=False)
    latency = round((time.time() - start) * 1000, 2)
    return {"status": "ok", "latency_ms": latency,
            "timestamp": datetime.now(timezone.utc).isoformat()}
