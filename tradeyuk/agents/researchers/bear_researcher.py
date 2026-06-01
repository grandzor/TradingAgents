from tradeyuk.agents.utils.agent_utils import get_language_instruction


def create_bear_researcher(llm):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        asset_type = state.get("asset_type", "stock")
        target_label = "saham" if asset_type == "stock" else "aset"
        lang = get_language_instruction()

        prompt = f"""Kamu adalah Analis Bearish dalam debat langsung dengan Analis Bullish tentang {target_label} ini.

ARGUMEN BULLISH TERBARU (yang harus kamu tanggapi langsung):
{current_response}

RIWAYAT DEBAT:
{history}

Tugasmu:
1. TANGGAPI langsung argumen bullish di atas - tunjukkan risiko dan kelemahannya
2. Bangun kasus bearish dengan data spesifik tentang risiko, valuasi, dan tantangan
3. Jika kamu SETUJU dengan poin bullish, AKUI dan gunakan "CONSENSUS_REACHED" untuk mengakhiri
4. Angkat risiko yang belum dibahas: makroekonomi, industri, regulasi

FOKUS PASAR INDONESIA: Jika saham IDX (.JK), pertimbangkan risiko nilai tukar IDR, kebijakan BI, volatilitas IHSG, dan ketergantungan komoditas.

Laporan tersedia:
- Pasar: {market_research_report[:500]}...
- Fundamental: {fundamentals_report[:500]}...
- Sentimen: {sentiment_report[:300]}...
- Berita: {news_report[:300]}...

BERDEBATLAH seperti percakapan nyata - sapa Analis Bullish, tanggapi spesifik argumennya, dan bangun menuju kesimpulan bersama. Jika kamu setuju dengan mayoritas poin bullish, nyatakan CONSENSUS_REACHED.
""" + lang

        response = llm.invoke(prompt)
        argument = f"Bear Analyst: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }
        return {"investment_debate_state": new_state}

    return bear_node
