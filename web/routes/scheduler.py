from pathlib import Path

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.scheduler import get_scheduler, _FREQ_LABELS

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/schedules", response_class=HTMLResponse)
async def schedules_page(request: Request):
    mgr = get_scheduler()
    schedules = mgr.list_schedules()
    return templates.TemplateResponse(
        request, "schedules.html", {"schedules": schedules, "freq_labels": _FREQ_LABELS}
    )


@router.get("/api/schedules")
async def api_list_schedules():
    mgr = get_scheduler()
    return JSONResponse(content=mgr.list_schedules())


@router.post("/api/schedules")
async def api_add_schedule(
    ticker: str = Form(...),
    frequency: str = Form(...),
    asset_type: str = Form("stock"),
):
    if frequency not in _FREQ_LABELS:
        raise HTTPException(status_code=400, detail="Frekuensi tidak valid")
    mgr = get_scheduler()
    sched = mgr.add_schedule(ticker, frequency, asset_type)
    return JSONResponse(content=sched, status_code=201)


@router.delete("/api/schedules/{schedule_id}")
async def api_remove_schedule(schedule_id: int):
    mgr = get_scheduler()
    if mgr.remove_schedule(schedule_id):
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")


@router.get("/api/schedules/{schedule_id}/results")
async def api_schedule_results(schedule_id: int):
    mgr = get_scheduler()
    sched = mgr.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

    import json
    from tradeyuk.default_config import DEFAULT_CONFIG

    results_dir = Path(DEFAULT_CONFIG["results_dir"]) / sched["ticker"].upper() / "TradeyukStrategy_logs"
    results = []
    if results_dir.exists():
        for log_file in sorted(results_dir.glob("full_states_log_*.json"), reverse=True):
            date_str = log_file.stem.replace("full_states_log_", "")
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                text = state.get("final_trade_decision", "")
                results.append({"date": date_str, "ticker": sched["ticker"], "decision": text[:200]})
            except Exception:
                results.append({"date": date_str, "ticker": sched["ticker"], "decision": "Gagal membaca"})

    return JSONResponse(content=results[:20])
