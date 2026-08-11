import asyncio
import logging

from celery import Celery
from celery.schedules import crontab

from config import get_settings
from signal_engine.agents.agent_15m import Agent15m
from signal_engine.agents.agent_15s import Agent15s
from signal_engine.agents.agent_1h import Agent1h
from signal_engine.agents.agent_1m import Agent1m
from signal_engine.agents.agent_3m import Agent3m
from signal_engine.agents.agent_5m import Agent5m
from signal_engine.trainer import train_all_timeframes

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery("alphapulse", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "agent-15s": {"task": "signal_engine.scheduler.run_agent_15s", "schedule": 15.0},
    "agent-1m": {"task": "signal_engine.scheduler.run_agent_1m", "schedule": 60.0},
    "agent-3m": {"task": "signal_engine.scheduler.run_agent_3m", "schedule": 180.0},
    "agent-5m": {"task": "signal_engine.scheduler.run_agent_5m", "schedule": 300.0},
    "agent-15m": {"task": "signal_engine.scheduler.run_agent_15m", "schedule": 900.0},
    "agent-1h": {"task": "signal_engine.scheduler.run_agent_1h", "schedule": 3600.0},
    "retrain-weekly": {
        "task": "signal_engine.scheduler.retrain_models",
        "schedule": crontab(day_of_week="sun", hour=3, minute=0),
    },
}


def run_async(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


@celery_app.task(name="signal_engine.scheduler.run_agent_15s")
def run_agent_15s() -> int:
    return len(run_async(Agent15s().run()))


@celery_app.task(name="signal_engine.scheduler.run_agent_1m")
def run_agent_1m() -> int:
    return len(run_async(Agent1m().run()))


@celery_app.task(name="signal_engine.scheduler.run_agent_3m")
def run_agent_3m() -> int:
    return len(run_async(Agent3m().run()))


@celery_app.task(name="signal_engine.scheduler.run_agent_5m")
def run_agent_5m() -> int:
    return len(run_async(Agent5m().run()))


@celery_app.task(name="signal_engine.scheduler.run_agent_15m")
def run_agent_15m() -> int:
    return len(run_async(Agent15m().run()))


@celery_app.task(name="signal_engine.scheduler.run_agent_1h")
def run_agent_1h() -> int:
    return len(run_async(Agent1h().run()))


@celery_app.task(name="signal_engine.scheduler.retrain_models")
def retrain_models() -> int:
    results = run_async(train_all_timeframes())
    return len(results)  # type: ignore[arg-type]
