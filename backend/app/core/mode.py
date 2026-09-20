"""LANDSAFE_MODE guard.

production (default) — real data only. Demo modules are not importable.
demo                 — every response carries DEMO DATA.

Demo code lives in backend/demo/ and is imported through require_demo_mode()
only. Nothing in backend/app/ may import backend.demo at module scope.
"""
from backend.app.core.config import settings

DEMO_LABEL = "DEMO DATA"


def is_demo() -> bool:
    return settings.LANDSAFE_MODE == "demo"


def is_production() -> bool:
    return settings.LANDSAFE_MODE == "production"


class DemoCodeInProductionError(RuntimeError):
    pass


def require_demo_mode(what: str) -> None:
    """Called at the top of every demo module. Raises in production."""
    if not is_demo():
        raise DemoCodeInProductionError(
            f"{what} is demo-only code and cannot run with "
            f"LANDSAFE_MODE={settings.LANDSAFE_MODE}. Set LANDSAFE_MODE=demo."
        )
