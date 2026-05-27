import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _fetch_yahoo(ticker: str) -> Optional[dict]:
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).fast_info
        return {
            "ticker": ticker,
            "price": getattr(info, "last_price", None)
            or getattr(info, "regular_market_previous_close", None),
            "previous_close": getattr(info, "regular_market_previous_close", None),
            "currency": getattr(info, "currency", "USD"),
        }
    except Exception:
        return None


def _fetch_indodax_tickers() -> Optional[dict]:
    try:
        resp = requests.get(
            "https://indodax.com/api/ticker_all", timeout=10,
            headers={"User-Agent": "Tradeyuk/0.2.5"}
        )
        resp.raise_for_status()
        return resp.json().get("tickers", {})
    except Exception:
        return None


@router.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request):
    return templates.TemplateResponse(request, "prices.html")


@router.get("/api/prices/antam")
async def api_antam():
    result = {"source": "proxy", "timestamp": datetime.now().isoformat(), "items": []}

    gold = _fetch_yahoo("GC=F")
    if gold and gold.get("price"):
        price_idr = gold["price"] * 16500
        result["items"].append(
            {
                "name": "Emas (Global GC=F)",
                "symbol": "GC=F",
                "price_usd": round(gold["price"], 2),
                "price_idr": round(price_idr, 2),
                "unit": "per troy ounce",
            }
        )

    silver = _fetch_yahoo("SI=F")
    if silver and silver.get("price"):
        result["items"].append(
            {
                "name": "Perak (Global SI=F)",
                "symbol": "SI=F",
                "price_usd": round(silver["price"], 2),
                "price_idr": round(silver["price"] * 16500, 2),
                "unit": "per troy ounce",
            }
        )

    if not result["items"]:
        result["items"].append(
            {
                "name": "Emas ANTAM",
                "symbol": "ANTAM",
                "price_idr": None,
                "unit": "per gram",
                "note": "Data API logammulia.com tidak tersedia. Gunakan GC=F sebagai proksi.",
            }
        )

    return JSONResponse(content=result)


@router.get("/api/prices/crypto/id")
async def api_crypto_id():
    result = {"source": "indodax", "timestamp": datetime.now().isoformat(), "items": []}

    tickers = _fetch_indodax_tickers()
    if tickers:
        key_pairs = ["btc_idr", "eth_idr", "usdt_idr", "xrp_idr", "doge_idr", "sol_idr", "link_idr"]
        for pair in key_pairs:
            if pair in tickers:
                t = tickers[pair]
                result["items"].append(
                    {
                        "pair": pair.upper(),
                        "last": float(t.get("last", 0)),
                        "high": float(t.get("high", 0)),
                        "low": float(t.get("low", 0)),
                        "vol": float(t.get("vol_" + pair.split("_")[0], 0)),
                        "change": float(t.get("last", 0)) - float(t.get("buy", float(t.get("last", 0)))),
                    }
                )
    else:
        result["error"] = "Gagal mengambil data dari Indodax"

    return JSONResponse(content=result)


@router.get("/api/prices/idx")
async def api_idx():
    result = {"source": "yahoo", "timestamp": datetime.now().isoformat(), "items": []}

    idx_tickers = {
        "^JKSE": "IHSG (Indeks Harga Saham Gabungan)",
        "BBCA.JK": "BCA",
        "BBRI.JK": "BRI",
        "TLKM.JK": "Telkom Indonesia",
        "ASII.JK": "Astra International",
        "UNVR.JK": "Unilever Indonesia",
        "BMRI.JK": "Bank Mandiri",
        "ADRO.JK": "Adaro Energy",
        "ICBP.JK": "Indofood CBP",
        "INDF.JK": "Indofood",
    }

    for ticker, name in idx_tickers.items():
        data = _fetch_yahoo(ticker)
        if data and data.get("price"):
            result["items"].append(
                {
                    "name": name,
                    "symbol": ticker,
                    "price": data["price"],
                    "currency": data.get("currency", "IDR"),
                }
            )

    if not result["items"]:
        result["error"] = "Gagal mengambil data IDX"

    return JSONResponse(content=result)
