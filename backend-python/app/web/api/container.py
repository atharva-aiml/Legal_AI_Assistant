"""Composition root for the public API: wires every application service to
its real (SQL / filesystem / in-process AI) adapter, once per process."""

from app.application.activity_service import ActivityService
from app.application.auth_service import AuthService
from app.application.client_service import ClientService
from app.application.deadline_service import DeadlineService
from app.application.document_service import DocumentService
from app.application.draft_generation_service import DraftGenerationService
from app.application.matter_chat_service import MatterChatService
from app.application.matter_service import MatterService
from app.application.matter_view_service import MatterViewService
from app.application.notification_service import NotificationScanService, NotificationService
from app.application.preferences_service import LawyerPreferencesService
from app.application.search_service import RecentSearchService, SearchService
from app.application.template_service import TemplateService
from app.infrastructure.ai_bridges import InProcessChatGateway, InProcessIngestionTrigger
from app.infrastructure.file_storage import LocalFilesystemStorage
from app.infrastructure.notification_scheduler import NotificationScanScheduler
from app.infrastructure.password_hasher import BcryptPasswordHasher
from app.infrastructure.persistence.auth_repositories import SqlLawyerPreferencesRepository, SqlLawyerRepository, SqlSessionRepository
from app.infrastructure.persistence.client_matter_repositories import (
    SqlChatMessageRepository,
    SqlClientRepository,
    SqlMatterRepository,
    SqlMatterViewRepository,
)
from app.infrastructure.persistence.connection import SqlUnitOfWork
from app.infrastructure.persistence.deadline_document_repositories import SqlDeadlineRepository, SqlDocumentRepository
from app.infrastructure.persistence.notification_repository import SqlNotificationRepository
from app.infrastructure.persistence.search_repositories import SqlRecentSearchRepository, SqlSearchRepository
from app.infrastructure.persistence.template_repository import SqlTemplateRepository

unit_of_work = SqlUnitOfWork()

lawyer_repository = SqlLawyerRepository()
preferences_repository = SqlLawyerPreferencesRepository()
client_repository = SqlClientRepository()
matter_repository = SqlMatterRepository()
deadline_repository = SqlDeadlineRepository()
document_repository = SqlDocumentRepository()
notification_repository = SqlNotificationRepository()
template_repository = SqlTemplateRepository()

storage = LocalFilesystemStorage()
ingestion_trigger = InProcessIngestionTrigger(document_repository)

auth_service = AuthService(lawyer_repository, SqlSessionRepository(), BcryptPasswordHasher())
preferences_service = LawyerPreferencesService(preferences_repository)
document_service = DocumentService(document_repository, storage, ingestion_trigger)
draft_generation_service = DraftGenerationService(template_repository, document_repository, storage, ingestion_trigger)
deadline_service = DeadlineService(deadline_repository)
matter_service = MatterService(
    matter_repository, deadline_repository, document_service, SqlChatMessageRepository(), SqlMatterViewRepository(), unit_of_work
)
client_service = ClientService(client_repository, matter_repository, matter_service, unit_of_work)
matter_view_service = MatterViewService(SqlMatterViewRepository())
chat_service = MatterChatService(InProcessChatGateway())
activity_service = ActivityService(document_service, deadline_service, chat_service)
notification_service = NotificationService(notification_repository)
search_service = SearchService(SqlSearchRepository())
recent_search_service = RecentSearchService(SqlRecentSearchRepository())
template_service = TemplateService(template_repository)

notification_scheduler = NotificationScanScheduler(
    NotificationScanService(deadline_repository, notification_repository, lawyer_repository, preferences_repository)
)
