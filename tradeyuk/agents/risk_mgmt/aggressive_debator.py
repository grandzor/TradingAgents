from tradeyuk.agents.utils.agent_utils import get_language_instruction


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        trader_decision = state["trader_investment_plan"]
        lang = get_language_instruction()

        others = ""
        if current_conservative_response:
            others += f"Argumen Konservatif: {current_conservative_response[:800]}\n"
        if current_neutral_response:
            others += f"Argumen Netral: {current_neutral_response[:800]}\n"
        if not others:
            others = "Belum ada argumen dari analis lain. Buat argumen agresif pertamamu."

        prompt = f"""Kamu adalah Analis Risiko Agresif dalam debat langsung dengan Analis Konservatif dan Netral tentang keputusan trading ini.

KEPUTUSAN TRADER:
{trader_decision}

{others}

RIWAYAT DEBAT:
{history}

TUGASMU:
1. TANGGAPI LANGSUNG argumen konservatif dan netral di atas
2. Perjuangkan strategi berani - potensi keuntungan tinggi layak diambil
3. Gunakan data spesifik dari laporan untuk mendukung posisimu
4. Jika kamu SETUJU dengan poin lawan, akui dan gunakan "CONSENSUS_REACHED"
5. BERDEBATLAH secara percakapan, bukan sekadar presentasi

FOKUS PASAR INDONESIA: Jika menyangkut saham IDX atau aset Indonesia, pertimbangkan dinamika IHSG, kebijakan BI, sentimen domestik.
""" + lang

        response = llm.invoke(prompt)
        argument = f"Aggressive Analyst: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }
        return {"risk_debate_state": new_state}

    return aggressive_node
