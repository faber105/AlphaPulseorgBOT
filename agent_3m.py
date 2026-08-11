from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent3m(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="3m", agent_id="agent_3m"))

