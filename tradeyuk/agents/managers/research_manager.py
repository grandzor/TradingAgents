"""Research Manager: turns the bull/bear debate into a structured investment plan for the trader."""

from __future__ import annotations

from tradeyuk.agents.schemas import ResearchPlan, render_research_plan
from tradeyuk.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradeyuk.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_research_manager(llm):
    structured_llm = bind_structured(llm, ResearchPlan, "Research Manager")

    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")

        investment_debate_state = state["investment_debate_state"]

        prompt = f"""Kamu adalah Manajer Riset yang bertugas mengevaluasi debat antara Analis Bullish dan Bearish, lalu menghasilkan SATU rencana investasi yang komprehensif.

{instrument_context}

---
**Skala Peringkat** (pilih salah satu):
- **Beli**: Keyakinan kuat pada tesis bullish
- **Overweight**: Pandangan konstruktif, tambah eksposur bertahap
- **Tahan**: Pandangan seimbang, pertahankan posisi
- **Underweight**: Pandangan hati-hati, kurangi eksposur
- **Jual**: Keyakinan kuat pada tesis bearish

Jangan ragu mengambil sikap tegas. Gunakan "Tahan" hanya jika bukti benar-benar seimbang.

---
**Riwayat Debat:**
{history}

SINTESISKAN debat ini menjadi SATU rekomendasi yang jelas dengan alasan spesifik dari data.""" + get_language_instruction()

        investment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_plan,
            "Research Manager",
        )

        new_investment_debate_state = {
            "judge_decision": investment_plan,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": investment_plan,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": investment_plan,
        }

    return research_manager_node
