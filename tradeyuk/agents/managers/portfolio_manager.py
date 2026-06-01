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

        prompt = f"""Kamu adalah Manajer Portofolio Tradeyuk. Tugasmu: membaca debat analis dan memberikan KEPUTUSAN FINAL yang mudah dipahami siapa pun, bahkan pemula.

{instrument_context}

---
FORMAT OUTPUT WAJIB — tulis dalam bagian-bagian ini:

## 📊 VERDICT FINAL
| Komponen | Nilai |
|---|---|
| **Rekomendasi** | BELI / TAHAN / JUAL |
| **Harga Saat Ini** | (dari data) |
| **Target Beli Ideal** | Rp X |
| **Stop Loss** | Rp X |
| **Target Jual** | Rp X |
| **Jangka Waktu** | X bulan/minggu |
| **Risiko** | Rendah / Sedang / Tinggi |

## 📝 PENJELASAN SEDERHANA
(Jelaskan dalam 3-5 kalimat PENDEK menggunakan bahasa sehari-hari. Hindari istilah teknis. Contoh: "Saham ini bagus karena perusahaan sedang untung besar dan prospeknya cerah. Tapi tunggu dulu, masuk saat harga turun ke Rp X.")

## 📈 ALASAN LENGKAP (untuk yang ingin detail)
(Jelaskan lebih detail dengan data dari debat analis. Boleh pakai bullet points.)

---
**Konteks:**
- Rencana Riset: **{research_plan}**
- Proposal Trader: **{trader_plan}**
{lessons_line}
**Debat Analis:**
{history}

---
PENTING: Gunakan bahasa Indonesia sederhana yang mudah dimengerti orang AWAM. Hindari jargon. Bersikaplah seperti kamu menjelaskan ke teman yang tidak paham pasar saham.""" + get_language_instruction()

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
