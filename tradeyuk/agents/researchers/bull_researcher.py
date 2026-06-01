from tradeyuk.agents.utils.agent_utils import get_language_instruction


def create_bull_researcher(llm):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        asset_type = state.get("asset_type", "stock")
        target_label = "saham" if asset_type == "stock" else "aset"
        lang = get_language_instruction()

        is_first_turn = not current_response

        if is_first_turn:
            prompt = f"""Kamu adalah Analis Bullish yang memperdebatkan kasus investasi untuk {target_label} ini.

Kamu sedang berdiskusi langsung dengan Analis Bearish. Anggap ini percakapan langsung - sapa lawan debatmu dan bangun argumen bullish yang kuat.

Tugasmu:
1. BUKA DEBAT: Mulai dengan argumen bullish yang komprehensif tentang potensi kenaikan
2. Tonjolkan potensi pertumbuhan, keunggulan kompetitif, sentimen positif
3. Gunakan data spesifik dari laporan di bawah ini
4. Akhiri dengan mengundang Analis Bearish untuk merespons

FOKUS PASAR INDONESIA: Jika ini saham IDX (.JK), pertimbangkan kondisi makro Indonesia, kebijakan Bank Indonesia, dan dinamika pasar domestik.

Jika kamu SETUJU dengan poin-poin bearish sebelumnya, akui dan gunakan kata "CONSENSUS_REACHED" untuk mengakhiri debat.

Laporan Pasar: {market_research_report}
Laporan Sentimen: {sentiment_report}
Laporan Berita: {news_report}
Laporan Fundamental: {fundamentals_report}
""" + lang
        else:
            prompt = f"""Kamu adalah Analis Bullish dalam debat langsung dengan Analis Bearish tentang {target_label} ini.

ARGUMEN BEARISH TERBARU (yang harus kamu tanggapi langsung):
{current_response}

RIWAYAT DEBAT:
{history}

Tugasmu:
1. TANGGAPI langsung argumen bearish di atas - tunjukkan kelemahannya
2. Pertahankan dan perkuat posisi bullish dengan bukti spesifik
3. Jika kamu SETUJU dengan poin bearish, AKUI dan gunakan "CONSENSUS_REACHED"
4. Angkat data baru dari laporan yang belum dibahas

Laporan tersedia:
- Pasar: {market_research_report[:500]}...
- Fundamental: {fundamentals_report[:500]}...
- Sentimen: {sentiment_report[:300]}...
- Berita: {news_report[:300]}...

BERDEBATLAH seperti percakapan nyata - sapa lawan debatmu, tanggapi spesifik, dan bangun menuju kesimpulan bersama.
""" + lang

        response = llm.invoke(prompt)
        argument = f"Bull Analyst: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }
        return {"investment_debate_state": new_state}

    return bull_node
