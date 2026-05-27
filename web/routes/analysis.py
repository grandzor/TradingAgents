import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from tradeyuk.default_config import DEFAULT_CONFIG
from tradeyuk.graph.trading_graph import TradeyukGraph

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_REPORT_FIELDS = [
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
]

_FIELD_LABELS = {
    "market_report": "Analisis Pasar",
    "sentiment_report": "Analisis Sentimen",
    "news_report": "Analisis Berita",
    "fundamentals_report": "Analisis Fundamental",
    "investment_plan": "Keputusan Tim Riset",
    "trader_investment_plan": "Rencana Tim Trading",
    "final_trade_decision": "Keputusan Manajemen Portofolio",
}

_RATING_KEYWORDS = {
    "beli": {"label": "Beli", "class": "buy"},
    "overweight": {"label": "Overweight", "class": "overweight"},
    "tahan": {"label": "Tahan", "class": "hold"},
    "underweight": {"label": "Underweight", "class": "underweight"},
    "jual": {"label": "Jual", "class": "sell"},
    "buy": {"label": "Beli", "class": "buy"},
    "hold": {"label": "Tahan", "class": "hold"},
    "sell": {"label": "Jual", "class": "sell"},
}


def _extract_rating(text: str) -> dict:
    """Extract rating from decision text."""
    if not text:
        return {"label": "Tahan", "class": "hold"}
    lower = text.lower()
    for keyword, info in _RATING_KEYWORDS.items():
        if keyword in lower:
            return info
    return {"label": "Tahan", "class": "hold"}


def _extract_price(text: str, keyword: str) -> Optional[str]:
    """Extract a price value near a keyword in text."""
    import re

    if not text:
        return None
    pattern = rf"{keyword}[:\s]*[Rp]?\s*([\d.,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/analyze", response_class=HTMLResponse)
async def analyze_start(
    request: Request,
    ticker: str = Form(...),
    date: str = Form(...),
    asset_type: str = Form("stock"),
):
    return templates.TemplateResponse(
        request,
        "analysis.html",
        {
            "ticker": ticker,
            "date": date,
            "asset_type": asset_type,
        },
    )


@router.get("/analyze/{ticker}/{date}", response_class=HTMLResponse)
async def view_analysis(request: Request, ticker: str, date: str):
    results_dir = Path(DEFAULT_CONFIG["results_dir"]) / ticker / "TradeyukStrategy_logs"
    log_path = results_dir / f"full_states_log_{date}.json"

    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        rating = _extract_rating(state.get("final_trade_decision", ""))
        entry_price = _extract_price(
            state.get("trader_investment_decision", ""), "harga masuk"
        ) or _extract_price(state.get("trader_investment_plan", ""), "harga masuk")
        stop_loss = _extract_price(
            state.get("trader_investment_decision", ""), "stop loss"
        ) or _extract_price(state.get("trader_investment_plan", ""), "stop loss")
        price_target = _extract_price(
            state.get("final_trade_decision", ""), "target harga"
        ) or _extract_price(state.get("investment_plan", ""), "target harga")

        return templates.TemplateResponse(
            request,
            "analysis_result.html",
            {
                "ticker": ticker,
                "date": date,
                "state": state,
                "rating": rating,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "price_target": price_target,
                "field_labels": _FIELD_LABELS,
            },
        )

    return templates.TemplateResponse(
        request,
        "analysis.html",
        {"ticker": ticker, "date": date, "asset_type": "stock"},
    )


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    results_dir = Path(DEFAULT_CONFIG["results_dir"])
    entries = []

    if results_dir.exists():
        for ticker_dir in sorted(results_dir.iterdir()):
            if not ticker_dir.is_dir():
                continue
            logs_dir = ticker_dir / "TradeyukStrategy_logs"
            if not logs_dir.exists():
                continue
            for log_file in sorted(logs_dir.glob("full_states_log_*.json"), reverse=True):
                date_str = log_file.stem.replace("full_states_log_", "")
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    rating = _extract_rating(
                        state.get("final_trade_decision", "")
                    )
                    entries.append(
                        {
                            "ticker": ticker_dir.name,
                            "date": date_str,
                            "rating": rating,
                            "company": state.get("company_of_interest", ticker_dir.name),
                        }
                    )
                except Exception:
                    entries.append(
                        {
                            "ticker": ticker_dir.name,
                            "date": date_str,
                            "rating": {"label": "Tidak Diketahui", "class": "hold"},
                            "company": ticker_dir.name,
                        }
                    )

    return templates.TemplateResponse(
        request, "history.html", {"entries": entries[:50]}
    )


@router.get("/api/analyze/stream")
async def stream_analysis(
    ticker: str = Query(...),
    date: str = Query(...),
    asset_type: str = Query("stock"),
):
    async def event_generator():
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def run_graph():
            try:
                config = DEFAULT_CONFIG.copy()
                selected_analysts = ["market", "social", "news", "fundamentals"]
                if asset_type == "crypto":
                    selected_analysts = ["market", "social", "news"]

                graph = TradeyukGraph(
                    selected_analysts, config=config, debug=False
                )
                init_state = graph.propagator.create_initial_state(
                    ticker, date, asset_type=asset_type
                )
                args = graph.propagator.get_graph_args()

                trace = []
                for chunk in graph.graph.stream(init_state, **args):
                    trace.append(chunk)
                    reports = {}
                    for field in _REPORT_FIELDS:
                        if chunk.get(field):
                            reports[field] = chunk[field]
                    if reports:
                        asyncio.run_coroutine_threadsafe(
                            q.put({"type": "progress", "reports": reports}), loop
                        )

                final_state = {}
                for c in trace:
                    final_state.update(c)

                result = {}
                for field in _REPORT_FIELDS:
                    result[field] = final_state.get(field, "")

                rating = _extract_rating(result.get("final_trade_decision", ""))
                result["rating"] = rating

                asyncio.run_coroutine_threadsafe(
                    q.put({"type": "done", "result": result}), loop
                )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    q.put({"type": "error", "message": str(e)}), loop
                )

        with ThreadPoolExecutor(max_workers=1) as executor:
            loop.run_in_executor(executor, run_graph)

            while True:
                data = await q.get()
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                if data["type"] in ("done", "error"):
                    break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/analyze")
async def api_analyze(
    ticker: str = Form(...),
    date: str = Form(...),
    asset_type: str = Form("stock"),
):
    try:
        config = DEFAULT_CONFIG.copy()
        selected_analysts = ["market", "social", "news", "fundamentals"]
        if asset_type == "crypto":
            selected_analysts = ["market", "social", "news"]

        graph = TradeyukGraph(selected_analysts, config=config, debug=False)
        final_state, signal = graph.propagate(
            ticker, date, asset_type=asset_type
        )

        result = {}
        for field in _REPORT_FIELDS:
            result[field] = final_state.get(field, "")
        result["signal"] = signal
        rating = _extract_rating(final_state.get("final_trade_decision", ""))
        result["rating"] = rating

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)}, status_code=500
        )
