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
