from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent1m(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="1m", agent_id="agent_1m"))

