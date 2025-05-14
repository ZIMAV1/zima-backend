
# routers/marketplace.py

from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from typing import List
from datetime import datetime
import os
from database import db
from utils.security import get_current_user

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

# ===============================
# Modelos
# ===============================
class SignalPurchase(BaseModel):
    signal_id: str
    buyer_id: str
    price_usd: float

class UsageLog(BaseModel):
    tenant_id: str
    api_calls: int
    signals_consumed: int
    executions: int

class Signal(BaseModel):
    asset: str
    timeframe: str
    prediction: str
    confidence: float
    timestamp: datetime

# ===============================
# Registrar uso por tenant (para SLA / billing)
# ===============================
@router.post("/log_usage")
async def log_usage(log: UsageLog, user=Depends(get_current_user)):
    if user.tenant_id != log.tenant_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    await db.usage_logs.insert_one({
        "tenant_id": log.tenant_id,
        "api_calls": log.api_calls,
        "signals_consumed": log.signals_consumed,
        "executions": log.executions,
        "timestamp": datetime.utcnow()
    })

    return {"status": "ok", "message": "✅ Uso registrado correctamente"}

# ===============================
# Comprar señal individual
# ===============================
@router.post("/buy_signal")
async def purchase_signal(purchase: SignalPurchase, user=Depends(get_current_user)):
    signal = await db.signals.find_one({"_id": purchase.signal_id})
    if not signal:
        raise HTTPException(status_code=404, detail="Señal no encontrada")

    await db.purchases.insert_one({
        "buyer_id": purchase.buyer_id,
        "signal_id": purchase.signal_id,
        "price_usd": purchase.price_usd,
        "timestamp": datetime.utcnow()
    })

    return {"status": "ok", "access_granted": True, "signal": signal}

# ===============================
# Listar señales públicas
# ===============================
@router.get("/public_signals", response_model=List[Signal])
async def list_public_signals():
    signals = await db.signals.find().sort("timestamp", -1).limit(20).to_list(20)
    return signals

# ===============================
# Dashboard público resumido
# ===============================
@router.get("/public_kpis")
async def get_public_metrics():
    total = await db.signals.count_documents({})
    last_signals = await db.signals.find().sort("timestamp", -1).limit(10).to_list(10)

    return {
        "kpis": {
            "total_signals": total,
            "roi_avg": "74.3%",
            "win_rate_avg": "88.1%",
            "sharpe": 1.92
        },
        "latest": last_signals
    }


# routers/marketplace.py

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import stripe
import os

from utils.security import get_current_user
from database import db

router = APIRouter()

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ---------- MODELOS ----------
class UsageLog(BaseModel):
    api_calls: int
    signals_consumed: int
    executions: int
    tenant_id: str

class SignalPurchaseRequest(BaseModel):
    signal_id: str
    buyer_id: str
    price_usd: float

class CheckoutSessionRequest(BaseModel):
    customer_id: str
    plan_id: str
    promo_code: str = None

# ---------- FACTURACIÓN POR USO ----------
@router.post("/api/billing/log_usage")
async def log_usage(log: UsageLog, user=Depends(get_current_user)):
    if user.tenant_id != log.tenant_id:
        raise HTTPException(status_code=403, detail="⛔ Acceso denegado")

    await db.usage_logs.insert_one({
        "tenant_id": log.tenant_id,
        "api_calls": log.api_calls,
        "signals_consumed": log.signals_consumed,
        "executions": log.executions,
        "timestamp": datetime.utcnow()
    })

    return {"status": "ok", "message": "✅ Uso registrado"}

# ---------- MARKETPLACE DE SEÑALES ----------
@router.post("/api/marketplace/purchase_signal")
async def purchase_signal(req: SignalPurchaseRequest, user=Depends(get_current_user)):
    signal = await db.signals.find_one({"_id": req.signal_id})
    if not signal:
        raise HTTPException(status_code=404, detail="❌ Señal no encontrada")

    await db.purchases.insert_one({
        "buyer_id": req.buyer_id,
        "signal_id": req.signal_id,
        "price_usd": req.price_usd,
        "timestamp": datetime.utcnow()
    })

    return {"status": "ok", "access_granted": True}

# ---------- STRIPE CHECKOUT DINÁMICO ----------
@router.post("/api/checkout/create")
async def create_checkout_session(req: CheckoutSessionRequest):
    try:
        session = stripe.checkout.Session.create(
            customer=req.customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": req.plan_id,
                "quantity": 1,
            }],
            mode="subscription",
            discounts=[{"coupon": req.promo_code}] if req.promo_code else [],
            success_url=os.getenv("SUCCESS_URL", "https://zima.ai/success"),
            cancel_url=os.getenv("CANCEL_URL", "https://zima.ai/cancel"),
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- WEBHOOK DE STRIPE ----------
@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook inválido: {str(e)}")

    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]
        plan_id = subscription["items"]["data"][0]["price"]["id"]
        await db.tenants.update_one(
            {"stripe_customer_id": customer_id},
            {"$set": {"active_plan_id": plan_id}}
        )

    return {"received": True}
