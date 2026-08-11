from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent15m(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="15m", agent_id="agent_15m"))

