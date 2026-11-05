import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

ON_CALL_TOOL_ALLOWLIST = (
    "read_redacted_readiness",
    "reset_stale_connection_pool",
    "verify_readiness",
)

logger = logging.getLogger("savorloop.on_call")
logger.setLevel(logging.INFO)
logger.propagate = True
if not logger.handlers:
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(audit_handler)


class ReadinessAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,80}$")
    alert_name: Literal["stale_sqlalchemy_connection_pool"]
    status: Literal["firing"]


@dataclass(frozen=True)
class ReadinessSignal:
    ready: bool
    error_category: str | None = None


def read_database_readiness(engine: Engine) -> ReadinessSignal:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return ReadinessSignal(ready=False, error_category="database_unavailable")
    return ReadinessSignal(ready=True)


class ReadinessTools:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def read_redacted_readiness(self) -> ReadinessSignal:
        return read_database_readiness(self._engine)

    def reset_stale_connection_pool(self) -> None:
        self._engine.dispose()

    def verify_readiness(self) -> ReadinessSignal:
        return read_database_readiness(self._engine)


class OnCallAgent:
    def __init__(self, engine: Engine) -> None:
        self._tools = ReadinessTools(engine)

    def handle_alert(self, alert: ReadinessAlert) -> dict:
        incident_id = str(uuid4())
        events: list[dict] = []

        def record(event_name: str, **attributes: object) -> None:
            event = {
                "event": event_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_id": alert.alert_id,
                "incident_id": incident_id,
                **attributes,
            }
            events.append(event)
            logger.info(json.dumps(event, sort_keys=True))

        record("alert.received", alert_name=alert.alert_name)
        record("agent.invoked", tool_allowlist=list(ON_CALL_TOOL_ALLOWLIST))

        diagnosis = self._tools.read_redacted_readiness()
        if diagnosis.ready:
            record("diagnosis.completed", diagnosis="readiness_already_available")
            outcome = "unresolved"
        elif diagnosis.error_category == "database_unavailable":
            record(
                "diagnosis.completed",
                diagnosis="stale_sqlalchemy_connection_pool",
                error_category=diagnosis.error_category,
            )
            record(
                "remediation.invoked",
                tool="reset_stale_connection_pool",
            )
            try:
                self._tools.reset_stale_connection_pool()
            except Exception:
                record(
                    "remediation.failed",
                    tool="reset_stale_connection_pool",
                    error_category="pool_reset_failed",
                )
            else:
                record(
                    "remediation.completed",
                    tool="reset_stale_connection_pool",
                )

            verification = self._tools.verify_readiness()
            record(
                "readiness.verified",
                readiness="ready" if verification.ready else "unavailable",
                error_category=verification.error_category,
            )
            outcome = "recovered" if verification.ready else "unresolved"
        else:
            record("diagnosis.completed", diagnosis="unknown_readiness_failure")
            outcome = "unresolved"

        record("incident.completed", outcome=outcome)
        return {
            "alert_id": alert.alert_id,
            "incident_id": incident_id,
            "outcome": outcome,
            "events": events,
        }
