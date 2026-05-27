from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradeyuk.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradeyuk.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradeyuk.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradeyuk.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)


def get_language_instruction() -> str:
    """Kembalikan instruksi prompt untuk bahasa output yang dikonfigurasi.

    Mengembalikan string kosong saat Bahasa Inggris (default), jadi tidak ada token tambahan yang digunakan.
    Diterapkan ke setiap agen yang outputnya mencapai laporan yang disimpan —
    analis, periset, debater, manajer riset, trader, dan
    manajer portofolio — sehingga proses non-Bahasa Indonesia menghasilkan laporan
    yang sepenuhnya terlokalisasi alih-alih campuran bahasa.
    """
    from tradeyuk.dataflows.config import get_config
    lang = get_config().get("output_language", "Bahasa Indonesia")
    if lang.strip().lower() == "english":
        return ""
    return f" Tulis seluruh respons Anda dalam bahasa {lang}."


def build_instrument_context(ticker: str, asset_type: str = "stock") -> str:
    """Deskripsikan instrumen yang tepat agar agen mempertahankan ticker berkualifikasi bursa."""
    instrument_label = "aset" if asset_type == "crypto" else "instrumen"
    extra_hint = (
        " Perlakukan sebagai aset kripto alih-alih perusahaan, dan jangan berasumsi bahwa fundamental perusahaan tersedia."
        if asset_type == "crypto"
        else ""
    )
    return (
        f"Instrumen {instrument_label} yang akan dianalisis adalah `{ticker}`. "
        "Gunakan ticker persis ini dalam setiap panggilan alat, laporan, dan rekomendasi, "
        "dengan mempertahankan sufiks bursa apa pun (mis. `.TO`, `.L`, `.HK`, `.T`, `-USD`)."
        + extra_hint
    )

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
