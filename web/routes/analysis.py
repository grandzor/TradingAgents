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


@router.get("/health")
async def health_check():
    try:
        from tradeyuk.llm_clients.factory import create_llm_client
        from tradeyuk.default_config import DEFAULT_CONFIG
        provider = DEFAULT_CONFIG.get("llm_provider", "?")
        c = create_llm_client(provider, DEFAULT_CONFIG["quick_think_llm"])
        llm = c.get_llm()
        key_set = llm.openai_api_key is not None
        return JSONResponse({
            "status": "ok",
            "provider": provider,
            "model": DEFAULT_CONFIG["quick_think_llm"],
            "base_url": llm.openai_api_base,
            "key_configured": key_set
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


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
    results_dir = Path(DEFAULT_CONFIG["results_dir"]) / ticker

    # Try JSON format first (TradeyukStrategy_logs)
    log_path = results_dir / "TradeyukStrategy_logs" / f"full_states_log_{date}.json"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        rating = _extract_rating(state.get("final_trade_decision", ""))
        entry_price = _extract_price(state.get("trader_investment_decision", ""), "harga masuk") or _extract_price(state.get("trader_investment_plan", ""), "harga masuk")
        stop_loss = _extract_price(state.get("trader_investment_decision", ""), "stop loss") or _extract_price(state.get("trader_investment_plan", ""), "stop loss")
        price_target = _extract_price(state.get("final_trade_decision", ""), "target harga") or _extract_price(state.get("investment_plan", ""), "target harga")
        return templates.TemplateResponse(request, "analysis_result.html", {
            "ticker": ticker, "date": date, "state": state,
            "rating": rating, "entry_price": entry_price,
            "stop_loss": stop_loss, "price_target": price_target,
        })

    # Try CLI format (TICKER/DATE/reports/*.md)
    cli_dir = results_dir / date / "reports"
    if cli_dir.exists():
        state = {}
        report_map = {
            "market_report.md": "market_report",
            "sentiment_report.md": "sentiment_report",
            "news_report.md": "news_report",
            "fundamentals_report.md": "fundamentals_report",
            "investment_plan.md": "investment_plan",
            "trader_investment_plan.md": "trader_investment_plan",
            "final_trade_decision.md": "final_trade_decision",
        }
        for filename, key in report_map.items():
            fpath = cli_dir / filename
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    state[key] = f.read()

        if state:
            rating = _extract_rating(state.get("final_trade_decision", ""))
            entry_price = _extract_price(state.get("trader_investment_plan", ""), "harga masuk")
            stop_loss = _extract_price(state.get("trader_investment_plan", ""), "stop loss")
            price_target = _extract_price(state.get("final_trade_decision", ""), "target harga") or _extract_price(state.get("investment_plan", ""), "target harga")
            return templates.TemplateResponse(request, "analysis_result.html", {
                "ticker": ticker, "date": date, "state": state,
                "rating": rating, "entry_price": entry_price,
                "stop_loss": stop_loss, "price_target": price_target,
            })

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

            # Format 1: TradeyukStrategy_logs/full_states_log_*.json (web app format)
            logs_dir = ticker_dir / "TradeyukStrategy_logs"
            if logs_dir.exists():
                for log_file in sorted(logs_dir.glob("full_states_log_*.json"), reverse=True):
                    date_str = log_file.stem.replace("full_states_log_", "")
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            state = json.load(f)
                        rating = _extract_rating(state.get("final_trade_decision", ""))
                        entries.append({
                            "ticker": ticker_dir.name,
                            "date": date_str,
                            "rating": rating,
                            "company": state.get("company_of_interest", ticker_dir.name),
                        })
                    except Exception:
                        entries.append({
                            "ticker": ticker_dir.name,
                            "date": date_str,
                            "rating": {"label": "Tidak Diketahui", "class": "hold"},
                            "company": ticker_dir.name,
                        })

            # Format 2: YYYY-MM-DD/reports/*.md (CLI format)
            for date_dir in sorted(ticker_dir.iterdir(), reverse=True):
                if not date_dir.is_dir():
                    continue
                date_str = date_dir.name
                if not date_str.replace("-", "").isdigit():
                    continue

                # Check if already covered by JSON format above
                already_exists = any(e["ticker"] == ticker_dir.name and e["date"] == date_str for e in entries)
                if already_exists:
                    continue

                reports_dir = date_dir / "reports"
                final_report = reports_dir / "final_trade_decision.md"
                if final_report.exists():
                    try:
                        with open(final_report, "r", encoding="utf-8") as f:
                            content = f.read()
                        rating = _extract_rating(content)
                        entries.append({
                            "ticker": ticker_dir.name,
                            "date": date_str,
                            "rating": rating,
                            "company": ticker_dir.name,
                        })
                    except Exception:
                        pass

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
                err_msg = str(e)
                if "OPENAI_API_KEY" in err_msg or "Missing credentials" in err_msg:
                    err_msg = (
                        f"Error kredensial LLM: {err_msg}\n\n"
                        "Pastikan Anda telah mengatur API key di file .env:\n"
                        "  DEEPSEEK_API_KEY=sk-...\n\n"
                        f"Provider saat ini: {DEFAULT_CONFIG.get('llm_provider', '?')}"
                    )
                asyncio.run_coroutine_threadsafe(
                    q.put({"type": "error", "message": err_msg}), loop
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


@router.get("/api/report/download")
async def download_report(ticker: str = Query(...), date: str = Query(...)):
    from fastapi.responses import StreamingResponse
    import io

    results_dir = Path(DEFAULT_CONFIG["results_dir"]) / ticker / "TradeyukStrategy_logs"
    log_path = results_dir / f"full_states_log_{date}.json"

    if not log_path.exists():
        return JSONResponse({"error": "Laporan tidak ditemukan"}, status_code=404)

    with open(log_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    rating = _extract_rating(state.get("final_trade_decision", ""))
    entry_price = _extract_price(state.get("trader_investment_decision", ""), "harga masuk") or _extract_price(state.get("trader_investment_plan", ""), "harga masuk")
    stop_loss = _extract_price(state.get("trader_investment_decision", ""), "stop loss") or _extract_price(state.get("trader_investment_plan", ""), "stop loss")
    price_target = _extract_price(state.get("final_trade_decision", ""), "target harga") or _extract_price(state.get("investment_plan", ""), "target harga")

    md = []
    md.append(f"# Laporan Analisis Tradeyuk")
    md.append(f"**Ticker:** {ticker}  ")
    md.append(f"**Tanggal:** {date}  ")
    md.append(f"**Dibuat:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"## 📊 Verdict Final")
    md.append("")
    md.append("| Komponen | Nilai |")
    md.append("|---|---|")
    md.append(f"| **Rekomendasi** | **{rating.get('label', '?')}** |")
    if entry_price:
        md.append(f"| Target Beli Ideal | Rp {entry_price} |")
    if stop_loss:
        md.append(f"| Stop Loss | Rp {stop_loss} |")
    if price_target:
        md.append(f"| Target Jual | Rp {price_target} |")
    md.append("")
    md.append("---")
    md.append("")

    for field, label in [
        ("market_report", "Analisis Pasar"),
        ("sentiment_report", "Analisis Sentimen"),
        ("news_report", "Analisis Berita"),
        ("fundamentals_report", "Analisis Fundamental"),
        ("investment_plan", "Keputusan Tim Riset"),
        ("trader_investment_plan", "Rencana Tim Trading"),
        ("final_trade_decision", "Keputusan Manajemen Portofolio"),
    ]:
        content = state.get(field, "")
        if content:
            md.append(f"## {label}")
            md.append("")
            md.append(content)
            md.append("")

    md.append("---")
    md.append(f"*Laporan dibuat oleh Tradeyuk — Framework Trading AI Multi-Agen*")
    md.append(f"*Powered by Grandzor*")

    report_text = "\n".join(md)

    return StreamingResponse(
        io.BytesIO(report_text.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=Tradeyuk_{ticker}_{date}.md"
        }
    )
