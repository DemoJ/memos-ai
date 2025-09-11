from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Memo(Base):
    __tablename__ = "memo"
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_ts = Column(Integer, nullable=False)
    updated_ts = Column(Integer, nullable=False)
    row_status = Column(String, default="NORMAL")
    visibility = Column(String, default="PRIVATE")
    
    @property
    def created_datetime(self):
        return datetime.fromtimestamp(self.created_ts)
    
    @property
    def updated_datetime(self):
        return datetime.fromtimestamp(self.updated_ts)

class VectorRecord(Base):
    __tablename__ = "vector_records"
    
    id = Column(Integer, primary_key=True)
    memo_id = Column(Integer, nullable=False, unique=True)
    content = Column(Text, nullable=False)
    embedding_id = Column(Integer, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)