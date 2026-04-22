import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 建立 SQLite 資料庫連線
DATABASE_URL = "sqlite:///./transfer_exam.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    region = Column(String(50), nullable=True)
    website_url = Column(String(255), nullable=True)
    
    departments = relationship("Department", back_populates="school")

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String(100), nullable=False, index=True)
    
    school = relationship("School", back_populates="departments")
    exam_infos = relationship("ExamInfo", back_populates="department")

class ExamInfo(Base):
    __tablename__ = "exam_infos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    year = Column(Integer, nullable=False)
    semester = Column(String(20), nullable=False)
    apply_start_date = Column(Date, nullable=True)
    apply_end_date = Column(Date, nullable=True)
    exam_date = Column(Date, nullable=True)
    quota = Column(Integer, nullable=True)
    restrictions = Column(Text, nullable=True)
    brochure_url = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    department = relationship("Department", back_populates="exam_infos")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_token = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String(20), nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
