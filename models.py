# -*- coding: utf-8 -*-
"""
数据模型定义模块
使用 SQLAlchemy ORM 定义数据库表结构
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
from config import Config

# 1. 声明基类
Base = declarative_base()

# 2. 定义 QA 记录的数据模型
class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime, default=datetime.datetime.now)
    timestamp = Column(String, default=lambda: datetime.datetime.now().isoformat())
    context = Column(Text, nullable=True)
    question = Column(Text, nullable=False)
    type = Column(String(50))
    options = Column(Text)
    answer = Column(Text, nullable=False)
    raw_ai_response = Column(Text)
    model = Column(String(100))

    def __repr__(self):
        return f"<QARecord(id={self.id}, question='{self.question[:30]}...')>"

# 3. 数据库初始化和会话管理
# 默认使用 SQLite，方便快速部署
DATABASE_URL = Config.DATABASE_URL if hasattr(Config, 'DATABASE_URL') else "sqlite:///db/dev.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()