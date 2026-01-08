"""Create database schema from SQLAlchemy models"""

import sys
from pathlib import Path


# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

from sqlalchemy import create_engine

from app.db.models.base import Base


# Create engine
engine = create_engine("mysql+pymysql://loadtest_user:LoadTest2024!SecurePass@localhost:3307/loadtest_db", echo=True)

print("Creating all tables from models...")
Base.metadata.create_all(engine)
print("Done!")
