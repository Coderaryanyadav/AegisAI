from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aegis_backend.database import User, TwoFactorSecret, RevokedToken

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).filter(User.id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).filter(User.email == email)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_user_count(self) -> int:
        stmt = select(func.count(User.id))
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def list_users(self) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(self, user: User) -> User:
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_two_factor_secret(self, user_id: int) -> Optional[TwoFactorSecret]:
        stmt = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create_two_factor_secret(self, secret: TwoFactorSecret) -> TwoFactorSecret:
        self.db.add(secret)
        await self.db.commit()
        return secret

    async def update_two_factor_secret(self, secret: TwoFactorSecret) -> TwoFactorSecret:
        await self.db.commit()
        return secret

    async def add_revoked_token(self, token: str) -> RevokedToken:
        db_token = RevokedToken(token=token)
        self.db.add(db_token)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
        return db_token
