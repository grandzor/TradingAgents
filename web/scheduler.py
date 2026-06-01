import json
import os
import threading
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from tradeyuk.default_config import DEFAULT_CONFIG

SCHEDULES_FILE = Path(os.path.expanduser("~")) / ".tradeyuk" / "schedules.json"

_ID_LOCK = threading.Lock()
_ID_COUNTER = [0]


def _load_schedules():
    if SCHEDULES_FILE.exists():
        with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_schedules(schedules):
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2)


def _next_id(schedules):
    with _ID_LOCK:
        existing = {s.get("id", 0) for s in schedules}
        while True:
            _ID_COUNTER[0] += 1
            if _ID_COUNTER[0] not in existing:
                return _ID_COUNTER[0]


_FREQ_MAP = {
    "daily": {"trigger": "cron", "hour": 7, "minute": 0},
    "weekly": {"trigger": "cron", "day_of_week": "mon", "hour": 7, "minute": 0},
    "every_4_hours": {"trigger": "interval", "hours": 4},
    "every_6_hours": {"trigger": "interval", "hours": 6},
    "every_12_hours": {"trigger": "interval", "hours": 12},
    "every_24_hours": {"trigger": "interval", "hours": 24},
}

_FREQ_LABELS = {
    "daily": "Harian",
    "weekly": "Mingguan",
    "every_4_hours": "Setiap 4 Jam",
    "every_6_hours": "Setiap 6 Jam",
    "every_12_hours": "Setiap 12 Jam",
    "every_24_hours": "Setiap 24 Jam",
}


def _build_trigger(freq):
    cfg = _FREQ_MAP.get(freq, _FREQ_MAP["daily"])
    if cfg["trigger"] == "cron":
        params = {k: v for k, v in cfg.items() if k != "trigger"}
        return CronTrigger(**params)
    else:
        params = {k: v for k, v in cfg.items() if k != "trigger"}
        return IntervalTrigger(**params)


class ScheduleManager:
    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._job_store = {}
        self._reload()

    def _reload(self):
        schedules = _load_schedules()
        for s in schedules:
            s.setdefault("enabled", True)
            s.setdefault("next_run", None)
            s.setdefault("last_run", None)
            s.setdefault("last_result", None)
            s.setdefault("asset_type", "stock")

    def _run_analysis(self, schedule_id: int):
        schedules = _load_schedules()
        sched = next((s for s in schedules if s.get("id") == schedule_id), None)
        if not sched:
            return

        ticker = sched["ticker"]
        asset_type = sched.get("asset_type", "stock")
        trade_date = datetime.now().strftime("%Y-%m-%d")

        try:
            from tradeyuk.graph.trading_graph import TradeyukGraph

            selected_analysts = ["market", "social", "news", "fundamentals"]
            if asset_type == "crypto":
                selected_analysts = ["market", "social", "news"]

            graph = TradeyukGraph(selected_analysts, config=DEFAULT_CONFIG.copy(), debug=False)
            graph.propagate(ticker, trade_date, asset_type=asset_type)

            self._update_last_result(schedule_id, {"status": "success", "date": trade_date})
        except Exception as e:
            self._update_last_result(schedule_id, {"status": "error", "date": trade_date, "message": str(e)})

    def _update_last_result(self, schedule_id: int, result: dict):
        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s["last_result"] = result
                break
        _save_schedules(schedules)

    def add_schedule(self, ticker: str, frequency: str, asset_type: str = "stock") -> dict:
        schedules = _load_schedules()
        sid = _next_id(schedules)
        sched = {
            "id": sid,
            "ticker": ticker.upper(),
            "frequency": frequency,
            "asset_type": asset_type,
            "enabled": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_run": None,
            "last_result": None,
            "next_run": None,
        }
        schedules.append(sched)
        _save_schedules(schedules)

        job = self._scheduler.add_job(
            self._run_analysis,
            trigger=_build_trigger(frequency),
            args=[sid],
            id=str(sid),
            name=f"{ticker.upper()} ({_FREQ_LABELS.get(frequency, frequency)})",
            replace_existing=True,
        )
        sched["next_run"] = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None
        _save_schedules(schedules)

        return sched

    def remove_schedule(self, schedule_id: int) -> bool:
        schedules = _load_schedules()
        new_schedules = [s for s in schedules if s.get("id") != schedule_id]
        if len(new_schedules) == len(schedules):
            return False
        _save_schedules(new_schedules)

        try:
            self._scheduler.remove_job(str(schedule_id))
        except Exception:
            pass
        return True

    def get_schedule(self, schedule_id: int) -> dict | None:
        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                return s
        return None

    def list_schedules(self) -> list:
        schedules = _load_schedules()
        for s in schedules:
            job = self._scheduler.get_job(str(s.get("id")))
            if job:
                s["next_run"] = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None
        return schedules

    def start(self):
        schedules = _load_schedules()
        for s in schedules:
            if not s.get("enabled", True):
                continue
            sid = s.get("id")
            if sid is None:
                continue
            freq = s.get("frequency", "daily")
            try:
                job = self._scheduler.add_job(
                    self._run_analysis,
                    trigger=_build_trigger(freq),
                    args=[sid],
                    id=str(sid),
                    name=f"{s.get('ticker', '?')} ({_FREQ_LABELS.get(freq, freq)})",
                    replace_existing=True,
                )
                s["next_run"] = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None
            except Exception:
                pass
        _save_schedules(schedules)
        self._scheduler.start()

    def shutdown(self):
        self._scheduler.shutdown(wait=False)


_scheduler_instance: ScheduleManager | None = None


def get_scheduler() -> ScheduleManager:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ScheduleManager()
        _scheduler_instance.start()
    return _scheduler_instance
