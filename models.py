# -*- coding: utf-8 -*-
"""
数据模型定义模块
使用 SQLAlchemy ORM 定义数据库表结构
"""
import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import Config

# 1. 声明基类
Base = declarative_base()


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


# 3. 数据库初始化和会话管理
# 默认使用 SQLite，方便快速部署
DATABASE_URL = Config.DATABASE_URL if hasattr(Config, "DATABASE_URL") else "sqlite:///db/dev.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
