# -*- coding: utf-8 -*-
"""
数据模型定义模块
使用 SQLAlchemy 2.0 ORM 定义数据库表结构
支持同步和异步数据库操作
"""
import datetime
from typing import AsyncGenerator, Generator

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from config import Config


# 1. 声明基类 (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass


# 2. 定义 QA 记录的数据模型
class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    timestamp = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())
    context = Column(Text, nullable=True)
    question = Column(Text, nullable=False, index=True)
    type = Column(String(50), index=True)
    options = Column(Text)
    answer = Column(Text, nullable=False)
    raw_ai_response = Column(Text)
    model = Column(String(100), index=True)

    def __repr__(self):
        return f"<QARecord(id={self.id}, question='{self.question[:30]}...')>"


# 3. 数据库配置
DATABASE_URL = Config.DATABASE_URL if hasattr(Config, "DATABASE_URL") else "sqlite:///db/dev.db"

# 同步引擎（用于向后兼容的同步操作）
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 异步引擎（用于 FastAPI）
ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def init_db():
    """初始化数据库，创建所有表（同步）"""
    Base.metadata.create_all(bind=engine)


async def init_db_async():
    """初始化数据库，创建所有表（异步）"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db() -> Generator[Session, None, None]:
    """同步数据库会话依赖（向后兼容）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """异步数据库会话依赖（FastAPI）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
