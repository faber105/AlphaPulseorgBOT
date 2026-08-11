from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent5m(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="5m", agent_id="agent_5m"))

