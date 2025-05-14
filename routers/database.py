
# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient

# === Configuración PostgreSQL ===
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://zima:zima123@localhost:5432/zimadb")
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Configuración MongoDB (async) ===
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
mongo_db = client[os.getenv("MONGO_DB", "zima_db")]

# === Acceso directo a colecciones ===
users_collection = mongo_db.get_collection("users")
signals_collection = mongo_db.get_collection("signals")
testimonials_collection = mongo_db.get_collection("testimonials")
validations_collection = mongo_db.get_collection("validations")
purchases_collection = mongo_db.get_collection("purchases")
usage_logs_collection = mongo_db.get_collection("usage_logs")
tenants_collection = mongo_db.get_collection("tenants")
founding_members_collection = mongo_db.get_collection("founding_members")
ui_configs_collection = mongo_db.get_collection("ui_configs")
