import uuid

from sqlalchemy import update

from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.repository import BaseRepository
from app.domain.work_order import OrderStatus


class WorkOrderRepository(BaseRepository[WorkOrder]):
    model = WorkOrder

    async def update_status_if(
        self, order_id: uuid.UUID, *, expected: OrderStatus, new: OrderStatus
    ) -> bool:
        """Cambia el estado solo si sigue siendo el leído. False si otro lo cambió antes."""
        stmt = (
            update(self.model)
            .where(
                self.model.id == order_id,
                self.model.status == expected,
                self.model.deleted_at.is_(None),
            )
            .values(status=new)
            .returning(self.model.id)
            .execution_options(synchronize_session=False)
        )
        return await self.session.scalar(stmt) is not None

    def add_event(self, event: WorkOrderEvent) -> None:
        self.session.add(event)
