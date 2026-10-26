from app.core.security import hash_password
from app.db.models.catalog import WorkType
from app.db.models.client import ClientSite
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder
from app.domain.work_order import OrderStatus


def make_user(
    *,
    email: str = "admin@ot-demo.com",
    password: str = "Secreta123",
    role: UserRole = UserRole.admin,
    full_name: str = "Admin de Prueba",
    is_active: bool = True,
) -> User:
    """Crea un usuario ficticio con la contraseña ya hasheada (datos de prueba)."""
    return User(
        email=email,
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        is_active=is_active,
    )


def make_work_order(
    *,
    client_site: ClientSite,
    work_type: WorkType,
    status: OrderStatus = OrderStatus.pending,
) -> WorkOrder:
    """Orden ficticia en el estado pedido, sin pasar por la máquina de estados."""
    return WorkOrder(
        client_id=client_site.client_id,
        client_site_id=client_site.id,
        work_type_id=work_type.id,
        status=status,
    )
