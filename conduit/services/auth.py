from sqlalchemy.ext.asyncio import AsyncSession

from conduit.core.exceptions import (
    EmailAlreadyTakenException,
    IncorrectJWTTokenException,
    IncorrectLoginInputException,
    UserNameAlreadyTakenException,
)
from conduit.core.security import verify_password
from conduit.domain.dtos.jwt import AuthTokenDTO
from conduit.domain.dtos.user import (
    CreatedUserDTO,
    CreateUserDTO,
    LoggedInUserDTO,
    LoginUserDTO,
    UpdateUserDTO,
    UserDTO,
)
from conduit.domain.repositories.user import IUserRepository
from conduit.domain.services.auth import IUserAuthService
from conduit.domain.services.jwt import IJWTTokenService


class UserAuthService(IUserAuthService):
    """Service to handle users auth logic."""

    def __init__(self, user_repo: IUserRepository, jwt_service: IJWTTokenService):
        self._user_repo = user_repo
        self._jwt_service = jwt_service

    async def get_current_user(self, session: AsyncSession, token: str) -> UserDTO:
        token_dto = AuthTokenDTO(token=token)
        user_id = self._jwt_service.get_user_id(token_dto=token_dto)
        if not user_id:
            raise IncorrectJWTTokenException()
        return await self._user_repo.get_by_id(session=session, user_id=user_id)

    async def sign_up_user(
        self, session: AsyncSession, user_to_create: CreateUserDTO
    ) -> CreatedUserDTO:
        if await self._user_repo.get_by_email(
            session=session, email=user_to_create.email
        ):
            raise EmailAlreadyTakenException()

        if await self._user_repo.get_by_username(
            session=session, username=user_to_create.username
        ):
            raise UserNameAlreadyTakenException()

        user = await self._user_repo.create(session=session, create_item=user_to_create)
        auth_token = self._jwt_service.generate_token(user=user)

        return CreatedUserDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            bio=user.bio,
            image=user.image_url,
            token=auth_token.token,
        )

    async def sign_in_user(
        self, session: AsyncSession, user_to_login: LoginUserDTO
    ) -> LoggedInUserDTO:
        user = await self._user_repo.get_by_email(
            session=session, email=user_to_login.email
        )
        if not user:
            raise IncorrectLoginInputException()

        if not verify_password(
            plain_password=user_to_login.password, hashed_password=user.password_hash
        ):
            raise IncorrectLoginInputException()

        auth_token = self._jwt_service.generate_token(user=user)
        return LoggedInUserDTO(
            email=user.email,
            username=user.username,
            bio=user.bio,
            image=user.image_url,
            token=auth_token.token,
        )

    async def update_user(
        self, session: AsyncSession, user_id: int, user_to_update: UpdateUserDTO
    ) -> UserDTO:
        return await self._user_repo.update(
            session=session, user_id=user_id, update_item=user_to_update
        )
