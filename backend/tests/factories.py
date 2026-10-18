from app.core.security import hash_password
from app.db.models.user import User, UserRole


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
