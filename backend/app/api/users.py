import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.user import UserAdminOut, UserCreate, UserUpdate
from app.db.models.user import User, UserRole
from app.services import users as users_service

router = APIRouter(prefix="/admin/users", tags=["usuarios"])

# Solo administración y dirección gestionan usuarios (ver roles-permisos.md).
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: SessionDep, _: AdminOrOwner) -> User:
    try:
        return await users_service.create_user(session, payload)
    except users_service.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "email_already_exists",
                "message": "Ya existe un usuario con ese correo.",
            },
        ) from None


@router.get("", response_model=list[UserAdminOut])
async def list_users(session: SessionDep, _: AdminOrOwner) -> Sequence[User]:
    return await users_service.list_users(session)


@router.get("/{user_id}", response_model=UserAdminOut)
async def get_user(user_id: uuid.UUID, session: SessionDep, _: AdminOrOwner) -> User:
    try:
        return await users_service.get_user(session, user_id)
    except users_service.UserNotFoundError:
        raise _not_found() from None


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: uuid.UUID, payload: UserUpdate, session: SessionDep, _: AdminOrOwner
) -> User:
    try:
        return await users_service.update_user(session, user_id, payload)
    except users_service.UserNotFoundError:
        raise _not_found() from None


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(user_id: uuid.UUID, session: SessionDep, _: AdminOrOwner) -> None:
    try:
        await users_service.deactivate_user(session, user_id)
    except users_service.UserNotFoundError:
        raise _not_found() from None


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "user_not_found", "message": "No se encontró el usuario."},
    )
