"""Pengambilan data pasar kripto dari Indodax (bursa kripto Indonesia).

Indodax menyediakan API publik tanpa perlu kunci API untuk data ticker
dan ringkasan pasar. Modul ini mengambil harga kripto dalam Rupiah (IDR)
dari endpoint publik https://indodax.com/api/.

Setiap fungsi memiliki error handling dan timeout; mengembalikan nilai
default yang aman jika request gagal, sehingga pemanggil tidak perlu
menangani None atau exception secara khusus.

Pemetaan simbol: BTC -> btc_idr, ETH -> eth_idr, dsb.
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_API_BASE = "https://indodax.com/api"
_UA = "tradeyuk/0.2 (+https://github.com/Grandzor/Tradeyuk)"

# Simbol umum ke pasangan Indodax
_SYMBOL_TO_PAIR: dict[str, str] = {
    "BTC": "btc_idr",
    "ETH": "eth_idr",
    "USDT": "usdt_idr",
    "BNB": "bnb_idr",
    "SOL": "sol_idr",
    "XRP": "xrp_idr",
    "ADA": "ada_idr",
    "DOGE": "doge_idr",
    "AVAX": "avax_idr",
    "MATIC": "matic_idr",
    "DOT": "dot_idr",
    "LINK": "link_idr",
    "UNI": "uni_idr",
    "AAVE": "aave_idr",
    "SAND": "sand_idr",
    "LTC": "ltc_idr",
    "TRX": "trx_idr",
    "ATOM": "atom_idr",
    "XTZ": "xtz_idr",
    "BCH": "bch_idr",
    "COMP": "comp_idr",
    "YFI": "yfi_idr",
    "SNX": "snx_idr",
    "GRT": "grt_idr",
    "1INCH": "1inch_idr",
    "ENJ": "enj_idr",
    "MANA": "mana_idr",
    "ZIL": "zil_idr",
    "THETA": "theta_idr",
    "OCEAN": "ocean_idr",
    "AGIX": "agix_idr",
    "FET": "fet_idr",
    "NEAR": "near_idr",
    "APT": "apt_idr",
    "ARB": "arb_idr",
    "OP": "op_idr",
    "SUI": "sui_idr",
    "SEI": "sei_idr",
    "PEPE": "pepe_idr",
    "SHIB": "shib_idr",
    "WIF": "wif_idr",
    "BONK": "bonk_idr",
    "TIA": "tia_idr",
    "STRK": "strk_idr",
}


def _symbol_to_pair(symbol: str) -> str:
    """Konversi simbol kripto umum ke pasangan Indodax.

    Menerima format: 'BTC', 'btc', 'btc_idr', 'BTC_IDR', dsb.
    Mengembalikan pasangan lowercase seperti 'btc_idr'.
    """
    symbol_clean = symbol.strip().upper()

    # Jika sudah dalam format pair_idr
    low = symbol.strip().lower()
    if low.endswith("_idr"):
        return low

    # Cek pemetaan simbol
    if symbol_clean in _SYMBOL_TO_PAIR:
        return _SYMBOL_TO_PAIR[symbol_clean]

    # Coba tebak: lowercase + _idr
    return f"{symbol_clean.lower()}_idr"


def get_indodax_ticker(pair: str = "btc_idr", timeout: float = 10.0) -> dict:
    """Ambil data ticker untuk pasangan kripto tertentu di Indodax.

    Args
        pair: Pasangan perdagangan, misal "btc_idr", "eth_idr".
        timeout: Timeout request dalam detik.

    Returns
        dict dengan data ticker; dict kosong jika gagal.
        Struktur khas Indodax:
        {
            "ticker": {
                "high": "980000000",
                "low": "950000000",
                "last": "965000000",
                "vol_btc": "12.5",
                "vol_idr": "12000000000",
                "buy": "964000000",
                "sell": "966000000",
            }
        }
    """
    url = f"{_API_BASE}/ticker/{pair.lower()}"
    headers_dict = {
        "User-Agent": _UA,
        "Accept": "application/json",
    }
    try:
        req = Request(url, headers=headers_dict)
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            if isinstance(data, dict):
                return data
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError) as exc:
        logger.warning("Indodax ticker request gagal untuk %s: %s", pair, exc)
    return {}


def get_indodax_summaries(timeout: float = 15.0) -> dict:
    """Ambil ringkasan pasar semua pasangan di Indodax.

    Endpoint ini memberikan data ringkasan untuk seluruh pasangan
    perdagangan yang tersedia di Indodax.

    Args
        timeout: Timeout request dalam detik.

    Returns
        dict dengan kunci pasangan dan data ringkasan; dict kosong jika gagal.
    """
    url = f"{_API_BASE}/summaries"
    headers_dict = {
        "User-Agent": _UA,
        "Accept": "application/json",
    }
    try:
        req = Request(url, headers=headers_dict)
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            if isinstance(data, dict):
                return data
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError) as exc:
        logger.warning("Indodax summaries request gagal: %s", exc)
    return {}


def _extract_tickers_from_summaries(summaries: dict) -> dict[str, dict]:
    """Ekstrak data ticker dari respons summaries (bisa nested atau flat)."""
    if not summaries:
        return {}
    # Respons API Indodax biasanya membungkus data di bawah kunci 'tickers'
    nested = summaries.get("tickers")
    if isinstance(nested, dict):
        return nested
    # Jika flat, gunakan langsung (fallback)
    if any(isinstance(v, dict) for v in summaries.values()):
        return summaries
    return {}


def get_all_idr_markets(timeout: float = 15.0) -> dict[str, dict]:
    """Ambil semua pasangan kripto berdenominasi IDR dan harga terkininya.

    Menyaring ringkasan pasar untuk hanya menampilkan pasangan yang
    berakhiran '_idr'.

    Args
        timeout: Timeout request dalam detik.

    Returns
        dict dengan format {pair: {last, high, low, vol_idr, ...}, ...}
    """
    summaries = get_indodax_summaries(timeout=timeout)
    tickers = _extract_tickers_from_summaries(summaries)
    idr_markets = {}
    for pair, data in tickers.items():
        if isinstance(data, dict) and pair.lower().endswith("_idr"):
            idr_markets[pair] = data
    return idr_markets


def get_crypto_price_idr(symbol: str, timeout: float = 10.0) -> Optional[float]:
    """Ambil harga kripto dalam Rupiah (IDR) berdasarkan simbol.

    Args
        symbol: Simbol kripto, misal "BTC", "ETH", "SOL".
                Juga menerima format "btc_idr".
        timeout: Timeout request dalam detik.

    Returns
        Harga terakhir dalam IDR sebagai float, atau None jika gagal.
    """
    pair = _symbol_to_pair(symbol)
    ticker = get_indodax_ticker(pair, timeout=timeout)
    ticker_data = ticker.get("ticker", {}) if isinstance(ticker, dict) else {}
    last = ticker_data.get("last")
    if last is not None:
        try:
            return float(last)
        except (ValueError, TypeError):
            logger.warning("Nilai 'last' tidak valid untuk %s: %s", pair, last)
    return None


def get_top_idr_volume(limit: int = 10, timeout: float = 15.0) -> list[dict]:
    """Ambil kripto dengan volume IDR tertinggi di Indodax.

    Args
        limit: Jumlah maksimum hasil yang dikembalikan.
        timeout: Timeout request dalam detik.

    Returns
        List dict terurut berdasarkan volume IDR menurun, dengan format:
        [{"pair": "btc_idr", "last": 965000000, "vol_idr": 12000000000, ...}, ...]
    """
    idr_markets = get_all_idr_markets(timeout=timeout)
    ranked = []
    for pair, data in idr_markets.items():
        try:
            vol_idr = float(data.get("vol_idr", 0))
        except (ValueError, TypeError):
            vol_idr = 0.0
        try:
            last = float(data.get("last", 0))
        except (ValueError, TypeError):
            last = 0.0
        entry = {
            "pair": pair,
            "last": last,
            "vol_idr": vol_idr,
            "high": data.get("high"),
            "low": data.get("low"),
        }
        ranked.append(entry)

    ranked.sort(key=lambda x: x["vol_idr"], reverse=True)
    return ranked[:limit]


def get_multiple_prices_idr(
    symbols: list[str], timeout: float = 15.0
) -> dict[str, Optional[float]]:
    """Ambil harga beberapa kripto sekaligus dalam IDR.

    Menggunakan endpoint summaries untuk efisiensi (satu request).
    Jika summaries tidak tersedia, fallback ke request per simbol.

    Args
        symbols: List simbol kripto, misal ["BTC", "ETH", "SOL"].
        timeout: Timeout request dalam detik.

    Returns
        dict dengan format {symbol: price_float | None}.
    """
    summaries = get_all_idr_markets(timeout=timeout)
    result: dict[str, Optional[float]] = {}

    for symbol in symbols:
        pair = _symbol_to_pair(symbol)
        data = summaries.get(pair)
        if data and isinstance(data, dict):
            last = data.get("last")
            try:
                result[symbol.upper()] = float(last) if last else None
            except (ValueError, TypeError):
                result[symbol.upper()] = None
        else:
            # Fallback: request per simbol
            result[symbol.upper()] = get_crypto_price_idr(symbol, timeout=timeout)

    return result


def get_indodax_24h_stats(symbol: str, timeout: float = 10.0) -> dict:
    """Ambil statistik 24 jam untuk kripto tertentu.

    Args
        symbol: Simbol kripto, misal "BTC", "ETH".
        timeout: Timeout request dalam detik.

    Returns
        dict dengan harga dan volume; dict kosong jika gagal.
    """
    pair = _symbol_to_pair(symbol)
    ticker = get_indodax_ticker(pair, timeout=timeout)
    ticker_data = ticker.get("ticker", {}) if isinstance(ticker, dict) else {}
    if not ticker_data:
        return {}

    def _to_float(val) -> Optional[float]:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    return {
        "pair": pair,
        "last_idr": _to_float(ticker_data.get("last")),
        "high_24h_idr": _to_float(ticker_data.get("high")),
        "low_24h_idr": _to_float(ticker_data.get("low")),
        "vol_idr_24h": _to_float(ticker_data.get("vol_idr")),
        "vol_asset_24h": _to_float(ticker_data.get("vol_" + pair.split("_")[0])),
        "buy_idr": _to_float(ticker_data.get("buy")),
        "sell_idr": _to_float(ticker_data.get("sell")),
    }
