from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent15s(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="15s", agent_id="agent_15s"))

