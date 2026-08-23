"""FastAPI application entry point."""

from fastapi import FastAPI

from support_agent.adapters import JsonKnowledgeRepository, SqliteLifecycleRepository
from support_agent.api.routes.assist import router as assist_router
from support_agent.api.routes.health import router as health_router
from support_agent.api.routes.lifecycle import router as lifecycle_router
from support_agent.config import Settings
from support_agent.services import (
    AssistService,
    RecommendationLifecycleService,
    WeightedLexicalRetriever,
)


def create_app(
    settings: Settings | None = None,
    assist_service: AssistService | None = None,
) -> FastAPI:
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
    if assist_service is None:
        repository = JsonKnowledgeRepository.from_path(resolved_settings.knowledge_path)
        assist_service = AssistService(
            repository,
            WeightedLexicalRetriever(repository),
            reference_date=resolved_settings.freshness_reference_date,
            freshness_max_age_days=resolved_settings.freshness_max_age_days,
        )
    application.state.lifecycle_service = RecommendationLifecycleService(
        assist_service,
        SqliteLifecycleRepository(resolved_settings.lifecycle_db_path),
    )
    application.include_router(health_router)
    application.include_router(assist_router)
    application.include_router(lifecycle_router)
    return application


app = create_app()
