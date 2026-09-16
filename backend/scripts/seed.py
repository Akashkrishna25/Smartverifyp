"""Seed database with default users. Run: python scripts/seed.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password

def seed():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@smartverify.com").first():
            db.add(User(name="Admin User", email="admin@smartverify.com",
                        password=hash_password("admin123"), role=UserRole.admin))
        if not db.query(User).filter(User.email == "officer@smartverify.com").first():
            db.add(User(name="Loan Officer", email="officer@smartverify.com",
                        password=hash_password("officer123"), role=UserRole.loan_officer))
        db.commit()
        print("Seed complete.")
        print("  Admin:   admin@smartverify.com / admin123")
        print("  Officer: officer@smartverify.com / officer123")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
