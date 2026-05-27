"""Pengambilan data harga emas dan perak ANTAM (Aneka Tambang).

ANTAM melalui Logam Mulia mempublikasikan harga emas dan perak harian
di https://www.logammulia.com. Modul ini mengambil data tersebut dan
menyediakan fallback jika pengambilan gagal.

Hasil di-cache selama 1 jam untuk menghindari permintaan berlebih.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_API_BASE = "https://www.logammulia.com"
_API_PRICES = f"{_API_BASE}/api/v1/prices"
_ALT_API_PRICES = f"{_API_BASE}/api/prices"
_UA = "tradeyuk/0.2 (+https://github.com/Grandzor/Tradeyuk)"

_CACHE_DURATION = timedelta(hours=1)

_ANTAM_CACHE: dict = {}
"""Cache untuk data harga ANTAM."""

# Harga default per gram (IDR) — perkiraan konservatif per 2025-2026.
# Harga riil berfluktuasi harian; gunakan ini hanya sebagai fallback.
_DEFAULT_GOLD_PRICE_PER_GRAM = 1_300_000
_DEFAULT_SILVER_PRICE_PER_GRAM = 15_000

# Bobot standar emas ANTAM (dalam gram)
_GOLD_WEIGHTS = [0.5, 1, 2, 3, 5, 10, 25, 50, 100, 250, 500, 1000]

# Bobot standar perak ANTAM (dalam gram)
_SILVER_WEIGHTS = [5, 10, 25, 50, 100, 250, 500, 1000]

# Premium harga per bobot — bobot lebih kecil = harga per gram lebih mahal.
# Faktor pengali diterapkan pada harga per gram dasar.
_WEIGHT_PREMIUM = {
    0.5: 1.08,
    1: 1.00,
    2: 0.99,
    3: 0.98,
    5: 0.97,
    10: 0.96,
    25: 0.95,
    50: 0.94,
    100: 0.93,
    250: 0.92,
    500: 0.91,
    1000: 0.90,
}


def _build_default_prices(gold_per_gram: int, silver_per_gram: int) -> dict:
    """Bangun struktur harga default untuk emas dan perak."""
    gold_prices = {}
    for w in _GOLD_WEIGHTS:
        premium = _WEIGHT_PREMIUM.get(w, 1.0)
        gold_prices[str(w)] = round(gold_per_gram * w * premium)

    silver_prices = {}
    for w in _SILVER_WEIGHTS:
        premium = _WEIGHT_PREMIUM.get(w, 1.0)
        silver_prices[str(w)] = round(silver_per_gram * w * premium)

    now = datetime.now().isoformat()
    return {
        "source": "default_fallback",
        "fetched_at": now,
        "gold": {
            "per_gram_idr": gold_per_gram,
            "prices_by_weight": gold_prices,
            "unit": "IDR",
        },
        "silver": {
            "per_gram_idr": silver_per_gram,
            "prices_by_weight": silver_prices,
            "unit": "IDR",
        },
    }


def _is_cache_valid() -> bool:
    """Periksa apakah cache masih berlaku."""
    ts = _ANTAM_CACHE.get("_timestamp")
    if ts is None:
        return False
    return (datetime.now() - ts) < _CACHE_DURATION


def _fetch_antam_api() -> Optional[dict]:
    """Ambil data harga dari API Logam Mulia.

    Returns dict jika berhasil, None jika gagal.
    """
    headers_dict = {
        "User-Agent": _UA,
        "Accept": "application/json, text/html",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    }

    endpoints = [_API_PRICES, _ALT_API_PRICES]
    for endpoint in endpoints:
        try:
            req = Request(endpoint, headers=headers_dict)
            with urlopen(req, timeout=10) as resp:
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError:
                    text = body.decode("latin-1")

                if "json" in content_type:
                    return json.loads(text)
                # Beberapa endpoint mengembalikan HTML dengan JSON tersemat
                if text:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        # Coba ekstrak JSON dari HTML
                        match = re.search(
                            r'(?:prices|data)\s*[:=]\s*(\[.*?\]|\{.*?\})',
                            text,
                            re.DOTALL,
                        )
                        if match:
                            try:
                                return json.loads(match.group(1))
                            except json.JSONDecodeError:
                                pass
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.debug("ANTAM API request failed for %s: %s", endpoint, exc)
            continue

    return None


def _parse_api_response(data: dict) -> dict:
    """Parse respons API menjadi struktur standar harga ANTAM."""
    now = datetime.now().isoformat()
    result = {
        "source": "api",
        "fetched_at": now,
        "gold": {"per_gram_idr": None, "prices_by_weight": {}, "unit": "IDR"},
        "silver": {"per_gram_idr": None, "prices_by_weight": {}, "unit": "IDR"},
    }

    # Berbagai kemungkinan struktur respons API
    items = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("data") or data.get("prices") or data.get("items") or []

    if not items:
        return result

    for item in items:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or item.get("product_name") or "").lower()
        weight = item.get("weight") or item.get("weight_gram") or item.get("gram")
        price = item.get("price") or item.get("sell_price") or item.get("harga")

        if not name or price is None:
            continue

        try:
            weight_float = float(weight) if weight else None
            price_int = int(price)
        except (ValueError, TypeError):
            continue

        if "emas" in name or "gold" in name:
            result["gold"]["prices_by_weight"][str(weight_float)] = price_int
            if weight_float == 1.0:
                result["gold"]["per_gram_idr"] = price_int
        elif "perak" in name or "silver" in name:
            result["silver"]["prices_by_weight"][str(weight_float)] = price_int
            if weight_float == 1.0:
                result["silver"]["per_gram_idr"] = price_int

    # Jika tidak ada harga per gram eksplisit, hitung dari bobot 0.5g
    if result["gold"]["per_gram_idr"] is None:
        gp = result["gold"]["prices_by_weight"]
        if "0.5" in gp:
            result["gold"]["per_gram_idr"] = int(gp["0.5"] / 0.5)
        elif "1" in gp:
            result["gold"]["per_gram_idr"] = gp["1"]

    if result["silver"]["per_gram_idr"] is None:
        sp = result["silver"]["prices_by_weight"]
        if "1" in sp:
            result["silver"]["per_gram_idr"] = sp["1"]
        elif "5" in sp:
            result["silver"]["per_gram_idr"] = int(sp["5"] / 5)

    return result


def _refresh_cache() -> dict:
    """Perbarui cache dengan data terbaru (API atau fallback)."""
    data = _fetch_antam_api()
    if data is not None:
        try:
            parsed = _parse_api_response(data)
            # Hanya gunakan hasil API jika ada data yang berarti
            if parsed["gold"]["prices_by_weight"] or parsed["silver"]["prices_by_weight"]:
                _ANTAM_CACHE["data"] = parsed
                _ANTAM_CACHE["_timestamp"] = datetime.now()
                return parsed
        except Exception as exc:
            logger.warning("Gagal parsing respons API ANTAM: %s", exc)

    # Fallback ke harga default
    fallback = _build_default_prices(
        _DEFAULT_GOLD_PRICE_PER_GRAM, _DEFAULT_SILVER_PRICE_PER_GRAM
    )
    _ANTAM_CACHE["data"] = fallback
    _ANTAM_CACHE["_timestamp"] = datetime.now()
    logger.warning("Menggunakan harga default ANTAM (API tidak tersedia)")
    return fallback


def _get_cached_or_refresh() -> dict:
    """Ambil data dari cache atau perbarui jika kedaluwarsa."""
    if _is_cache_valid() and "data" in _ANTAM_CACHE:
        return _ANTAM_CACHE["data"]
    return _refresh_cache()


def get_antam_prices() -> dict:
    """Ambil seluruh data harga emas dan perak ANTAM.

    Returns
        dict dengan struktur:
        {
            "source": "api" | "default_fallback",
            "fetched_at": "<ISO timestamp>",
            "gold": {
                "per_gram_idr": int,
                "prices_by_weight": {"0.5": int, "1": int, ...},
                "unit": "IDR",
            },
            "silver": {
                "per_gram_idr": int,
                "prices_by_weight": {"5": int, "10": int, ...},
                "unit": "IDR",
            },
        }
    """
    return _get_cached_or_refresh()


def get_antam_gold_price() -> int:
    """Ambil harga emas ANTAM per gram saat ini dalam Rupiah (IDR).

    Returns
        Harga emas per gram dalam IDR. Fallback ke ~1.300.000 jika gagal.
    """
    data = _get_cached_or_refresh()
    price = data.get("gold", {}).get("per_gram_idr")
    if price is not None:
        return price
    return _DEFAULT_GOLD_PRICE_PER_GRAM


def get_antam_silver_price() -> int:
    """Ambil harga perak ANTAM per gram saat ini dalam Rupiah (IDR).

    Returns
        Harga perak per gram dalam IDR. Fallback ke ~15.000 jika gagal.
    """
    data = _get_cached_or_refresh()
    price = data.get("silver", {}).get("per_gram_idr")
    if price is not None:
        return price
    return _DEFAULT_SILVER_PRICE_PER_GRAM


def get_antam_gold_weights() -> dict[str, int]:
    """Ambil harga emas ANTAM untuk semua bobot standar.

    Returns
        dict dengan kunci bobot (str) dan nilai harga (int), misal
        {"0.5": 650000, "1": 1300000, "5": 6500000, ...}
    """
    data = _get_cached_or_refresh()
    prices = data.get("gold", {}).get("prices_by_weight", {})
    if prices:
        return dict(prices)
    gold_per_gram = data.get("gold", {}).get("per_gram_idr", _DEFAULT_GOLD_PRICE_PER_GRAM)
    fallback = _build_default_prices(gold_per_gram, _DEFAULT_SILVER_PRICE_PER_GRAM)
    return fallback["gold"]["prices_by_weight"]


def get_antam_silver_weights() -> dict[str, int]:
    """Ambil harga perak ANTAM untuk semua bobot standar.

    Returns
        dict dengan kunci bobot (str) dan nilai harga (int), misal
        {"5": 75000, "10": 150000, "100": 1500000, ...}
    """
    data = _get_cached_or_refresh()
    prices = data.get("silver", {}).get("prices_by_weight", {})
    if prices:
        return dict(prices)
    silver_per_gram = data.get("silver", {}).get(
        "per_gram_idr", _DEFAULT_SILVER_PRICE_PER_GRAM
    )
    fallback = _build_default_prices(_DEFAULT_GOLD_PRICE_PER_GRAM, silver_per_gram)
    return fallback["silver"]["prices_by_weight"]
