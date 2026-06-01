from tradeyuk.agents.utils.agent_utils import get_language_instruction


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")
        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        trader_decision = state["trader_investment_plan"]
        lang = get_language_instruction()

        others = ""
        if current_aggressive_response:
            others += f"Argumen Agresif: {current_aggressive_response[:800]}\n"
        if current_conservative_response:
            others += f"Argumen Konservatif: {current_conservative_response[:800]}\n"
        if not others:
            others = "Belum ada argumen dari analis lain. Buat argumen netral pertamamu."

        prompt = f"""Kamu adalah Analis Risiko Netral dalam debat langsung dengan Analis Agresif dan Konservatif tentang keputusan trading ini.

KEPUTUSAN TRADER:
{trader_decision}

{others}

RIWAYAT DEBAT:
{history}

TUGASMU:
1. TANGGAPI LANGSUNG argumen agresif dan konservatif di atas
2. Berikan perspektif SEIMBANG - akui poin valid dari kedua sisi
3. Advokasi strategi moderat yang mengambil jalan tengah
4. Jika kamu MERASA kedua sisi sudah mencapai titik temu yang masuk akal, gunakan "CONSENSUS_REACHED" untuk mengakhiri debat
5. BERDEBATLAH secara percakapan, bukan sekadar presentasi

FOKUS PASAR INDONESIA: Jika menyangkut saham IDX, pertimbangkan keseimbangan antara potensi pertumbuhan IHSG dan risiko volatilitas IDR.
""" + lang

        response = llm.invoke(prompt)
        argument = f"Neutral Analyst: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }
        return {"risk_debate_state": new_state}

    return neutral_node
