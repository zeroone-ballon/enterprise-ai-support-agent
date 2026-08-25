"""FastAPI application entry point."""

from fastapi import FastAPI

from support_agent.adapters import (
    JsonKnowledgeRepository,
    OpenAICompatibleGenerator,
    OpenAICompatibleHttpTransport,
    ServiceNowPdiExecutor,
    ServiceNowPdiIncidentReader,
    ServiceNowSandboxExecutor,
    SqliteLifecycleRepository,
    UnavailableGenerator,
)
from support_agent.api.routes.assist import router as assist_router
from support_agent.api.routes.health import router as health_router
from support_agent.api.routes.lifecycle import router as lifecycle_router
from support_agent.config import Settings
from support_agent.observability import configure_observability
from support_agent.services import (
    AssistService,
    GenerationCoordinator,
    RecommendationLifecycleService,
    WeightedLexicalRetriever,
)


def create_app(
    settings: Settings | None = None,
    assist_service: AssistService | None = None,
) -> FastAPI:
    """Create the application with explicit, testable dependencies."""

    resolved_settings = settings or Settings.from_environment()
    resolved_settings.validate_for_startup()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Auditable IT support decision support with evidence, evaluation, "
            "human approval, and an execution audit trail."
        ),
    )
    application.state.settings = resolved_settings
    configure_observability(application, resolved_settings.log_level)
    if assist_service is None:
        repository = JsonKnowledgeRepository.from_path(resolved_settings.knowledge_path)
        if resolved_settings.generation_mode == "deterministic":
            primary_generator = None
        elif resolved_settings.generation_mode == "llm":
            if all(
                (
                    resolved_settings.llm_base_url,
                    resolved_settings.llm_api_key,
                    resolved_settings.llm_model,
                )
            ):
                primary_generator = OpenAICompatibleGenerator(
                    OpenAICompatibleHttpTransport(
                        resolved_settings.llm_base_url,
                        resolved_settings.llm_api_key,
                        resolved_settings.llm_model,
                        timeout_seconds=resolved_settings.llm_timeout_seconds,
                    )
                )
            else:
                primary_generator = UnavailableGenerator()
        else:
            raise ValueError("GENERATION_MODE must be deterministic or llm")
        assist_service = AssistService(
            repository,
            WeightedLexicalRetriever(repository),
            reference_date=resolved_settings.freshness_reference_date,
            freshness_max_age_days=resolved_settings.freshness_max_age_days,
            generation=GenerationCoordinator(primary_generator),
        )
    lifecycle_repository = SqliteLifecycleRepository(resolved_settings.lifecycle_db_path)
    if all(
        (
            resolved_settings.servicenow_instance_url,
            resolved_settings.servicenow_username,
            resolved_settings.servicenow_password,
        )
    ):
        application.state.servicenow_incident_reader = ServiceNowPdiIncidentReader(
            resolved_settings.servicenow_instance_url,
            resolved_settings.servicenow_username,
            resolved_settings.servicenow_password,
            timeout_seconds=resolved_settings.servicenow_timeout_seconds,
        )
    else:
        application.state.servicenow_incident_reader = None
    if resolved_settings.execution_mode == "sandbox":
        executor = ServiceNowSandboxExecutor(resolved_settings.lifecycle_db_path)
    elif resolved_settings.execution_mode == "servicenow_pdi":
        executor = ServiceNowPdiExecutor(
            resolved_settings.servicenow_instance_url,
            resolved_settings.servicenow_username,
            resolved_settings.servicenow_password,
            timeout_seconds=resolved_settings.servicenow_timeout_seconds,
        )
    else:
        raise ValueError("EXECUTION_MODE must be sandbox or servicenow_pdi")
    application.state.lifecycle_service = RecommendationLifecycleService(
        assist_service,
        lifecycle_repository,
        executor=executor,
    )
    application.include_router(health_router)
    application.include_router(assist_router)
    application.include_router(lifecycle_router)
    return application


app = create_app()
