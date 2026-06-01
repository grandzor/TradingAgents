from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_TICKER_DATA = {
    "categories": [
        {
            "name": "Saham IDX",
            "icon": "chart-line",
            "tickers": [
                {"symbol": "BBCA.JK", "name": "Bank Central Asia Tbk", "sector": "Perbankan"},
                {"symbol": "BBRI.JK", "name": "Bank Rakyat Indonesia Tbk", "sector": "Perbankan"},
                {"symbol": "BMRI.JK", "name": "Bank Mandiri Tbk", "sector": "Perbankan"},
                {"symbol": "BBNI.JK", "name": "Bank Negara Indonesia Tbk", "sector": "Perbankan"},
                {"symbol": "TLKM.JK", "name": "Telkom Indonesia Tbk", "sector": "Telekomunikasi"},
                {"symbol": "ASII.JK", "name": "Astra International Tbk", "sector": "Otomotif"},
                {"symbol": "UNVR.JK", "name": "Unilever Indonesia Tbk", "sector": "Barang Konsumsi"},
                {"symbol": "HMSP.JK", "name": "HM Sampoerna Tbk", "sector": "Rokok"},
                {"symbol": "ICBP.JK", "name": "Indofood CBP Sukses Makmur Tbk", "sector": "Makanan & Minuman"},
                {"symbol": "INDF.JK", "name": "Indofood Sukses Makmur Tbk", "sector": "Makanan & Minuman"},
                {"symbol": "UNTR.JK", "name": "United Tractors Tbk", "sector": "Alat Berat"},
                {"symbol": "ADRO.JK", "name": "Adaro Energy Indonesia Tbk", "sector": "Batubara"},
                {"symbol": "PTBA.JK", "name": "Bukit Asam Tbk", "sector": "Batubara"},
                {"symbol": "ITMG.JK", "name": "Indo Tambangraya Megah Tbk", "sector": "Batubara"},
                {"symbol": "ANTM.JK", "name": "Aneka Tambang Tbk", "sector": "Pertambangan"},
                {"symbol": "INCO.JK", "name": "Vale Indonesia Tbk", "sector": "Pertambangan"},
                {"symbol": "TINS.JK", "name": "Timah Tbk", "sector": "Pertambangan"},
                {"symbol": "MEDC.JK", "name": "Medco Energi Internasional Tbk", "sector": "Energi"},
                {"symbol": "PGAS.JK", "name": "Perusahaan Gas Negara Tbk", "sector": "Energi"},
                {"symbol": "EXCL.JK", "name": "XL Axiata Tbk", "sector": "Telekomunikasi"},
                {"symbol": "GOTO.JK", "name": "GoTo Gojek Tokopedia Tbk", "sector": "Teknologi"},
                {"symbol": "BUKA.JK", "name": "Bukalapak.com Tbk", "sector": "Teknologi"},
                {"symbol": "EMTK.JK", "name": "Elang Mahkota Teknologi Tbk", "sector": "Teknologi"},
                {"symbol": "ACES.JK", "name": "Ace Hardware Indonesia Tbk", "sector": "Ritel"},
                {"symbol": "MAPI.JK", "name": "Mitra Adiperkasa Tbk", "sector": "Ritel"},
                {"symbol": "CPIN.JK", "name": "Charoen Pokphand Indonesia Tbk", "sector": "Pakan Ternak"},
                {"symbol": "JPFA.JK", "name": "Japfa Comfeed Indonesia Tbk", "sector": "Pakan Ternak"},
                {"symbol": "SMGR.JK", "name": "Semen Indonesia Tbk", "sector": "Semen"},
                {"symbol": "INTP.JK", "name": "Indocement Tunggal Prakarsa Tbk", "sector": "Semen"},
                {"symbol": "BRPT.JK", "name": "Barito Pacific Tbk", "sector": "Petrokimia"},
            ],
        },
        {
            "name": "Kripto",
            "icon": "bitcoin",
            "tickers": [
                {"symbol": "BTC-USD", "name": "Bitcoin USD"},
                {"symbol": "ETH-USD", "name": "Ethereum USD"},
                {"symbol": "SOL-USD", "name": "Solana USD"},
                {"symbol": "ADA-USD", "name": "Cardano USD"},
                {"symbol": "XRP-USD", "name": "XRP USD"},
                {"symbol": "DOGE-USD", "name": "Dogecoin USD"},
                {"symbol": "DOT-USD", "name": "Polkadot USD"},
                {"symbol": "AVAX-USD", "name": "Avalanche USD"},
                {"symbol": "MATIC-USD", "name": "Polygon USD"},
            ],
        },
        {
            "name": "Emas & Perak",
            "icon": "coins",
            "tickers": [
                {"symbol": "GC=F", "name": "Emas / Gold Futures"},
                {"symbol": "SI=F", "name": "Perak / Silver Futures"},
                {"symbol": "XAUUSD=X", "name": "Gold Spot USD"},
                {"symbol": "XAGUSD=X", "name": "Silver Spot USD"},
                {"symbol": "GLD", "name": "SPDR Gold Trust ETF"},
                {"symbol": "SLV", "name": "iShares Silver Trust ETF"},
            ],
        },
        {
            "name": "Forex",
            "icon": "exchange-alt",
            "tickers": [
                {"symbol": "USDIDR=X", "name": "USD/IDR"},
                {"symbol": "EURUSD=X", "name": "EUR/USD"},
                {"symbol": "GBPUSD=X", "name": "GBP/USD"},
                {"symbol": "USDJPY=X", "name": "USD/JPY"},
                {"symbol": "AUDUSD=X", "name": "AUD/USD"},
                {"symbol": "USDSGD=X", "name": "USD/SGD"},
            ],
        },
        {
            "name": "Komoditas",
            "icon": "oil-can",
            "tickers": [
                {"symbol": "CL=F", "name": "Minyak Mentah WTI"},
                {"symbol": "NG=F", "name": "Gas Alam"},
                {"symbol": "ZC=F", "name": "Jagung / Corn Futures"},
                {"symbol": "ZS=F", "name": "Kedelai / Soybean Futures"},
            ],
        },
        {
            "name": "Indeks",
            "icon": "chart-bar",
            "tickers": [
                {"symbol": "^JKSE", "name": "IHSG - Indeks Harga Saham Gabungan"},
                {"symbol": "^GSPC", "name": "S&P 500"},
                {"symbol": "^DJI", "name": "Dow Jones Industrial Average"},
                {"symbol": "^IXIC", "name": "NASDAQ Composite"},
                {"symbol": "EIDO", "name": "iShares MSCI Indonesia ETF"},
            ],
        },
    ]
}


@router.get("/api/tickers")
async def get_tickers():
    return JSONResponse(content=_TICKER_DATA)
