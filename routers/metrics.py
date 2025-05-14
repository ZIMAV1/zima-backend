
# routers/metrics.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime
import random
import json
import os

router = APIRouter()

# Ruta de simulación para métricas
METRICS_PATH = "data/metrics.json"
os.makedirs("data", exist_ok=True)

# ================================
# MODELOS
# ================================
class KPI(BaseModel):
    total_signals: int
    win_rate: float
    avg_rating: float
    avg_roi: float
    active_users: int
    model_version: str
    updated_at: datetime

# ================================
# Helpers de lectura
# ================================
def load_metrics() -> Dict:
    if not os.path.exists(METRICS_PATH):
        return {
            "total_signals": 4200,
            "win_rate": 0.864,
            "avg_rating": 4.6,
            "avg_roi": 0.72,
            "active_users": 137,
            "model_version": "ZIMA-RL-v5",
            "updated_at": datetime.utcnow().isoformat()
        }
    with open(METRICS_PATH, "r") as f:
        return json.load(f)

# ================================
# ENDPOINT: KPIs globales (públicos)
# ================================
@router.get("/metrics/kpis", response_model=KPI)
async def get_kpis():
    data = load_metrics()
    return KPI(**data)

# ================================
# ENDPOINT: Métricas específicas de una señal
# ================================
@router.get("/metrics/signal/{signal_id}")
async def get_signal_metrics(signal_id: str):
    # Simulación de feedback por señal (reemplazar con DB)
    fake_feedback = [
        {"rating": random.randint(3, 5), "was_profitable": random.choice([True, True, False])}
        for _ in range(random.randint(5, 20))
    ]
    if not fake_feedback:
        raise HTTPException(status_code=404, detail="No hay métricas para esa señal")

    avg_rating = sum(f["rating"] for f in fake_feedback) / len(fake_feedback)
    win_rate = sum(1 for f in fake_feedback if f["was_profitable"]) / len(fake_feedback)

    return {
        "signal_id": signal_id,
        "feedback_count": len(fake_feedback),
        "avg_rating": round(avg_rating, 2),
        "win_rate": round(win_rate * 100, 2)
    }

# ================================
# ENDPOINT: Dashboard público (resumen)
# ================================
@router.get("/public/dashboard")
async def public_dashboard_summary():
    data = load_metrics()
    return {
        "status": "✅ ZIMA Metrics API Online",
        "global_metrics": {
            "signals_generated": data["total_signals"],
            "average_roi": f"{round(data['avg_roi'] * 100, 2)}%",
            "win_rate": f"{round(data['win_rate'] * 100, 2)}%",
            "active_users": data["active_users"],
            "model_version": data["model_version"]
        },
        "last_update": data["updated_at"]
    }


# routers/metrics.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from utils.security import get_current_user
from database import db

router = APIRouter(prefix="/metrics", tags=["KPIs"])

# =============================
# Modelos
# =============================
class KPISummary(BaseModel):
    roi_month: float
    win_rate: float
    sharpe_ratio: float
    drawdown: float
    signals_last_24h: int
    total_signals: int
    updated_at: datetime

class UserSignalMetric(BaseModel):
    symbol: str
    timeframe: str
    roi: float
    win_rate: float
    avg_holding: float
    updated_at: datetime

# =============================
# KPIs Globales para dashboard
# =============================
@router.get("/global", response_model=KPISummary)
async def get_global_metrics():
    kpi = await db.kpis.find_one({"_id": "global"})
    if not kpi:
        raise HTTPException(status_code=404, detail="No hay métricas registradas")
    return KPISummary(**kpi)

# =============================
# KPIs por usuario logueado
# =============================
@router.get("/user", response_model=List[UserSignalMetric])
async def get_user_metrics(user=Depends(get_current_user)):
    metrics = await db.user_kpis.find({"user_id": user.id}).to_list(100)
    return [UserSignalMetric(**m) for m in metrics]

# =============================
# Endpoint de status del sistema
# =============================
@router.get("/status")
async def health_check():
    return {
        "status": "✅ ZIMA KPIs online",
        "timestamp": datetime.utcnow()
    }


# routers/metrics.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from database import db
from utils.security import get_current_user
import redis
import json

router = APIRouter(prefix="/metrics", tags=["metrics"])
r = redis.Redis(host="localhost", port=6379, db=0)

# ============================
# Modelos de respuesta
# ============================
class KPIResponse(BaseModel):
    roi: float
    win_rate: float
    drawdown: float
    sharpe: float
    total_signals: int
    updated_at: datetime

# ============================
# Endpoint: KPIs públicos
# ============================
@router.get("/public", response_model=KPIResponse)
async def get_public_kpis():
    data = r.get("public:kpis:latest")
    if not data:
        raise HTTPException(status_code=404, detail="KPIs no disponibles")
    parsed = json.loads(data)
    return KPIResponse(**parsed)

# ============================
# Endpoint: KPIs personalizados por usuario
# ============================
@router.get("/me", response_model=KPIResponse)
async def get_user_kpis(user=Depends(get_current_user)):
    key = f"user:kpis:{user.id}"
    data = r.get(key)
    if not data:
        raise HTTPException(status_code=404, detail="KPIs del usuario no disponibles")
    parsed = json.loads(data)
    return KPIResponse(**parsed)

# ============================
# Endpoint: KPI de señales totales históricas
# ============================
@router.get("/summary")
async def get_kpi_summary():
    count = await db.signals.count_documents({})
    last_signal = await db.signals.find().sort("created_at", -1).limit(1).to_list(1)
    return {
        "total_signals": count,
        "last_signal_at": last_signal[0]["created_at"] if last_signal else None,
        "active_model": "ZIMA-RL-Boosted-v5",
        "version": "1.0.154"
    }


# routers/metrics.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
import random

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

# Modelo de respuesta para métricas globales
class KPIMetrics(BaseModel):
    total_signals: int
    win_rate: float
    avg_roi: float
    drawdown_avg: float
    sharpe_ratio: float
    active_models: int
    last_updated: datetime

# Simulación — en producción debe venir desde Redis, DB o sistema de señales
def get_global_kpis() -> Dict:
    return {
        "total_signals": 21394,
        "win_rate": round(random.uniform(0.82, 0.91), 4),
        "avg_roi": round(random.uniform(0.53, 0.78), 4),
        "drawdown_avg": round(random.uniform(0.03, 0.07), 4),
        "sharpe_ratio": round(random.uniform(1.8, 2.4), 2),
        "active_models": 4,
        "last_updated": datetime.utcnow()
    }

@router.get("/global", response_model=KPIMetrics)
async def get_metrics():
    return get_global_kpis()


# routers/metrics.py

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List, Dict
import redis
import json

router = APIRouter(prefix="/metrics", tags=["KPIs & Metrics"])

# Redis config (se asume host local, en producción puede ir en .env)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# ===============================
# ENDPOINT: KPIs globales de ZIMA
# ===============================
@router.get("/kpis/global")
async def get_global_kpis():
    try:
        data = r.get("zima:kpis:global")
        if data:
            return json.loads(data)
        else:
            raise HTTPException(status_code=404, detail="No hay KPIs globales cargados.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer KPIs: {str(e)}")

# ===============================
# ENDPOINT: KPIs por usuario/tenant
# ===============================
@router.get("/kpis/tenant/{tenant_id}")
async def get_tenant_kpis(tenant_id: str):
    key = f"zima:kpis:tenant:{tenant_id}"
    try:
        data = r.get(key)
        if data:
            return json.loads(data)
        else:
            raise HTTPException(status_code=404, detail="No hay KPIs para ese tenant.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al acceder a Redis: {str(e)}")

# ===============================
# ENDPOINT: Últimas señales públicas
# ===============================
@router.get("/signals/public", response_model=List[Dict])
async def get_public_signals():
    try:
        signals = r.lrange("zima:signals:public", -10, -1)
        return [json.loads(s) for s in signals]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al recuperar señales: {str(e)}")

# ===============================
# ENDPOINT: Estado del sistema
# ===============================
@router.get("/status")
async def get_status():
    return {
        "status": "✅ Backend ZIMA online",
        "timestamp": datetime.utcnow().isoformat()
    }
