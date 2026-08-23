"""FastAPI application entry point."""

from fastapi import FastAPI

from support_agent.api.routes.health import router as health_router
from support_agent.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the application with explicit, testable dependencies."""

    resolved_settings = settings or Settings.from_environment()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Auditable IT support decision support with evidence, evaluation, "
            "human approval, and an execution audit trail."
        ),
    )
    application.state.settings = resolved_settings
    application.include_router(health_router)
    return application


app = create_app()

