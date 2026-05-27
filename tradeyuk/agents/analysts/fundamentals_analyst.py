from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradeyuk.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_insider_transactions,
    get_language_instruction,
)
from tradeyuk.dataflows.config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "Anda adalah seorang analis fundamental yang bertugas menganalisis informasi fundamental perusahaan selama seminggu terakhir. "
            "Tulis laporan komprehensif tentang informasi fundamental perusahaan seperti dokumen keuangan, profil perusahaan, "
            "laporan keuangan dasar, dan riwayat keuangan perusahaan untuk memberikan gambaran lengkap kepada trader. "
            "Untuk saham Indonesia (.JK) yang terdaftar di Bursa Efek Indonesia (IDX), perhatikan sektor-sektor utama: "
            "perbankan (BBCA, BBRI, BMRI), konsumen (ICBP, UNVR), pertambangan dan komoditas (ADRO, INCO, PTBA), "
            "telekomunikasi (TLKM), dan infrastruktur (PGAS). "
            "Laporan keuangan perusahaan Indonesia disajikan dalam Rupiah (IDR) — konversikan ke USD jika diperlukan untuk perbandingan global. "
            "Sertakan sebanyak mungkin detail. Berikan wawasan yang spesifik dan dapat ditindaklanjuti dengan bukti pendukung "
            "untuk membantu trader membuat keputusan yang tepat."
            + " Pastikan untuk menambahkan tabel Markdown di akhir laporan untuk mengatur poin-poin penting, terorganisir dan mudah dibaca."
            + " Gunakan alat yang tersedia: `get_fundamentals` untuk analisis perusahaan komprehensif, `get_balance_sheet`, `get_cashflow`, dan `get_income_statement` untuk laporan keuangan spesifik."
            + get_language_instruction(),
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " Jika Anda atau asisten lain memiliki PROPOSAL TRANSAKSI FINAL: **BELI/TAHAN/JUAL** atau hasil akhir,"
                    " awali respons Anda dengan PROPOSAL TRANSAKSI FINAL: **BELI/TAHAN/JUAL** agar tim tahu untuk berhenti."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
