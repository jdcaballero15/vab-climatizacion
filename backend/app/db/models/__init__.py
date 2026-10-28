from app.db.models.catalog import EquipmentType, Failure, Repair, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSegment, ClientSite, TaxCondition
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.legacy_reference import LegacyReference
from app.db.models.refresh_token import RefreshToken
from app.db.models.signature import Signature
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderClosure,
    WorkOrderClosurePhoto,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)

__all__ = [
    "Client",
    "ClientContact",
    "ClientSegment",
    "ClientSite",
    "Crew",
    "Equipment",
    "EquipmentType",
    "Failure",
    "FieldTechnician",
    "LegacyReference",
    "RefreshToken",
    "Repair",
    "Signature",
    "StoredFile",
    "Task",
    "TaxCondition",
    "User",
    "UserRole",
    "WorkOrder",
    "WorkOrderAssignment",
    "WorkOrderCancellation",
    "WorkOrderClosure",
    "WorkOrderClosurePhoto",
    "WorkOrderClosureTask",
    "WorkOrderClosureTechnician",
    "WorkOrderEvent",
    "WorkType",
]
