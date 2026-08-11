from signal_engine.base_agent import AgentConfig, BaseAgent


class Agent1h(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentConfig(timeframe="1h", agent_id="agent_1h"))

