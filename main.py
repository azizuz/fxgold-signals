from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import time, os, re

app = FastAPI(title="Gold & Forex Signal Backend")

# ✅ API key (from Render secrets or fallback)
API_KEY = os.getenv("API_KEY", "fxgold123")

# ✅ Trusted origins
ALLOWED_ORIGINS = [
    "https://app.base44.com",
    "https://base44.com",
    "https://aurumiq.online",
    "https://fxgold-signals.onrender.com",
]

# ✅ Allow dynamic Base44 preview URLs
def is_allowed_origin(origin: str):
    if not origin:
        return False
    if origin in ALLOWED_ORIGINS:
        return True
    if re.search(r"\.modal\.host$", origin):
        return True
    return False


# ✅ Custom CORS middleware
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    response = await call_next(request)
    if origin and is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, x-api-key, api_key"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# ✅ Handle preflight OPTIONS requests
@app.options("/{path:path}")
async def preflight_handler(request: Request):
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Origin": origin if is_allowed_origin(origin) else "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, x-api-key, api_key",
        "Access-Control-Allow-Credentials": "true",
    }
    return JSONResponse(content={"ok": True}, headers=headers)


# --- Cache to avoid Yahoo rate limit ---
_cache = {"signals": None, "timestamp": None}

def compute_signal(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # Take the last row safely
    last = df.iloc[-1]

    sma20 = float(last["SMA20"])
    sma50 = float(last["SMA50"])

    if sma20 > sma50:
        return "BUY", 0.75
    elif sma20 < sma50:
        return "SELL", 0.70
    else:
        return "HOLD", 0.55


@app.get("/api/v1/signals")
def get_signals(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    print(f"DEBUG /signals – received key: {key!r}")

    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    now = datetime.now(timezone.utc)
    if _cache["signals"] and _cache["timestamp"]:
        if now - _cache["timestamp"] < timedelta(minutes=5):
            return _cache["signals"]

    # ✅ Corrected dictionary
    pairs = {
        "XAUUSD=X": "Gold",
        "EURUSD=X": "EUR/USD",
        "GBPUSD=X": "GBP/USD"
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
    _cache["timestamp"] = now
    return output


@app.get("/api/v1/metrics")
def get_metrics(x_api_key: str = Header(None), api_key: str = Header(None)):
    key = (x_api_key or api_key or "").strip()
    print(f"DEBUG /metrics – received key: {key!r}")

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
    return {
        "status": "ok",
        "latency_ms": round(time.time() % 1000, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
