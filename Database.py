# Database.py
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager


load_dotenv()

# -------------------------------------------------------
# 1️⃣ DATABASE URL  (asyncmy instead of aiomysql)
# -------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# -------------------------------------------------------
# 2️⃣ Base Model
# -------------------------------------------------------
Base = declarative_base()

# -------------------------------------------------------
# 3️⃣ Engine (ASYNC)
# -------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=True,               # Set to False in production
    pool_pre_ping=True,
    pool_recycle=3600
)

# -------------------------------------------------------
# 4️⃣ Session Factory (ASYNC)
# -------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# -------------------------------------------------------
# 5️⃣ Dependency for FastAPI (gets session per request)
# -------------------------------------------------------
@asynccontextmanager
async def get_async_session():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

