from langchain_core.tools import tool
from typing import Annotated
from tradeyuk.dataflows.interface import route_to_vendor


@tool
def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Ambil data harga (OHLCV) untuk simbol ticker tertentu.
    Mendukung saham (AAPL, BBCA.JK, ASII.JK), kripto (BTC-USD, ETH-USD),
    komoditas (GC=F, SI=F, CL=F), forex (USDIDR=X), dan indeks (^JKSE).
    Menggunakan vendor core_stock_apis yang dikonfigurasi.
    Args:
        symbol (str): Simbol ticker, mis. AAPL, BBCA.JK, BTC-USD, GC=F, USDIDR=X
        start_date (str): Tanggal mulai dalam format yyyy-mm-dd
        end_date (str): Tanggal akhir dalam format yyyy-mm-dd
    Returns:
        str: Dataframe berformat berisi data harga untuk ticker dalam rentang tanggal yang ditentukan.
    """
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)
