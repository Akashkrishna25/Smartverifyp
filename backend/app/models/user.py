"""User ORM model."""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    loan_officer = "loan_officer"

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    password   = Column(String(255), nullable=False)
    role       = Column(SAEnum(UserRole), default=UserRole.loan_officer, nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow)
    applications = relationship("Application", back_populates="user")
