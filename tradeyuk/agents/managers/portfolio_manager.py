"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call.  The result is rendered
back to markdown for storage in ``final_trade_decision`` so memory log,
CLI display, and saved reports continue to consume the same shape they do
today.  When a provider does not expose structured output, the agent falls
back gracefully to free-text generation.
"""

from __future__ import annotations

from tradeyuk.agents.schemas import PortfolioDecision, render_pm_decision
from tradeyuk.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradeyuk.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )

        prompt = f"""Kamu adalah Manajer Portofolio yang bertugas menyintesis debat analis risiko dan memberikan KEPUTUSAN FINAL trading yang komprehensif.

{instrument_context}

---
**Skala Peringkat** (pilih salah satu):
- **Beli**: Masuk atau tambah posisi
- **Overweight**: Pandangan positif, tambah eksposur bertahap
- **Tahan**: Pertahankan posisi saat ini
- **Underweight**: Kurangi eksposur, ambil profit sebagian
- **Jual**: Keluar dari posisi

**Konteks:**
- Rencana Manajer Riset: **{research_plan}**
- Proposal Trader: **{trader_plan}**
{lessons_line}
**Debat Analis Risiko:**
{history}

---
Berikan SATU KEPUTUSAN FINAL yang tegas. Dukung dengan bukti spesifik dari debat dan data. Jangan ragu-ragu.""" + get_language_instruction()

        final_trade_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pm_decision,
            "Portfolio Manager",
        )

        new_risk_debate_state = {
            "judge_decision": final_trade_decision,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_trade_decision,
        }

    return portfolio_manager_node
