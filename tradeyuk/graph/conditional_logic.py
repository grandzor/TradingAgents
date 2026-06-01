# tradeyuk/graph/conditional_logic.py

from tradeyuk.agents.utils.agent_states import AgentState


_CONSENSUS_KEYWORDS = [
    "CONSENSUS_REACHED", "KESEPAKATAN", "saya setuju", "kami sepakat",
    "Saya setuju", "kami mencapai", "I agree", "We agree", "no further debate",
    "tidak perlu debat", "cukup", "sepakat",
]


def _detect_consensus(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _CONSENSUS_KEYWORDS)


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Sentiment"

    def should_continue_news(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        debate_state = state["investment_debate_state"]
        current = debate_state.get("current_response", "")
        history = debate_state.get("history", "")
        count = debate_state["count"]

        safety_ceiling = 6 * self.max_debate_rounds

        if count >= safety_ceiling:
            return "Research Manager"

        if _detect_consensus(current):
            debate_state["consensus_reached"] = True
            return "Research Manager"

        if current.startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        risk_state = state["risk_debate_state"]
        latest = risk_state.get("latest_speaker", "")
        count = risk_state["count"]

        safety_ceiling = 9 * self.max_risk_discuss_rounds

        if count >= safety_ceiling:
            return "Portfolio Manager"

        if _detect_consensus(latest):
            risk_state["consensus_reached"] = True
            return "Portfolio Manager"

        if latest.startswith("Aggressive"):
            return "Conservative Analyst"
        if latest.startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"
