from tradeyuk.agents.utils.agent_utils import get_language_instruction


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        conservative_history = risk_debate_state.get("conservative_history", "")
        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        trader_decision = state["trader_investment_plan"]
        lang = get_language_instruction()

        others = ""
        if current_aggressive_response:
            others += f"Argumen Agresif: {current_aggressive_response[:800]}\n"
        if current_neutral_response:
            others += f"Argumen Netral: {current_neutral_response[:800]}\n"
        if not others:
            others = "Belum ada argumen dari analis lain. Buat argumen konservatif pertamamu."

        prompt = f"""Kamu adalah Analis Risiko Konservatif dalam debat langsung dengan Analis Agresif dan Netral tentang keputusan trading ini.

KEPUTUSAN TRADER:
{trader_decision}

{others}

RIWAYAT DEBAT:
{history}

TUGASMU:
1. TANGGAPI LANGSUNG argumen agresif dan netral di atas
2. Prioritaskan keamanan modal - tunjukkan risiko yang terlewatkan
3. Advokasi strategi yang lebih hati-hati dengan data spesifik
4. Jika kamu SETUJU dengan poin lawan, akui dan gunakan "CONSENSUS_REACHED"
5. BERDEBATLAH secara percakapan, bukan sekadar presentasi

FOKUS PASAR INDONESIA: Jika menyangkut saham IDX atau aset Indonesia, pertimbangkan volatilitas IDR, batas ARA/ARB, dan risiko regulasi domestik.
""" + lang

        response = llm.invoke(prompt)
        argument = f"Conservative Analyst: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": argument,
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }
        return {"risk_debate_state": new_state}

    return conservative_node
