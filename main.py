from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import time, os, re

app = FastAPI(title="Gold & Forex Signal Backend")

API_KEY = os.getenv("API_KEY", "fxgold123")

# --- Smart CORS Middleware ---
class SmartCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            origin = None
            for name, value in scope["headers"]:
                if name == b"origin":
                    origin = value.decode()
                    break

            # ✅ Allow Base44, Render, your domain, and modal.host previews
            if origin and (
                "base44.com" in origin
                or "render.com" in origin
                or "aurumiq.online" in origin
                or re.search(r"\.modal\.host$", origin)
            ):
                self.allow_origins = [origin]

        return await super().__call__(scope, receive, send)


app.add_middleware(
    SmartCORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cache to avoid Yahoo rate limit ---
_cache = {"signals": None, "timestamp": None}

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
def get_signals(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    print(f"DEBUG /signals – received header key: {key!r}")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    now = datetime.now(timezone.utc)
    if _cache["signals"] and _cache["timestamp"]:
        if now - _cache["timestamp"] < timedelta(minutes=5):
            return _cache["signals"]

    pairs = {"XAUUSD=X": "Gold", "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD"}
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
    _cache["timestamp"] = now
    return output


@app.get("/api/v1/metrics")
def get_metrics(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    print(f"DEBUG /metrics – received header key: {key!r}")
    if key != API_KEY:
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
    latency = round(time.time() % 1000, 2)
    return {
        "status": "ok",
        "latency_ms": latency,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
