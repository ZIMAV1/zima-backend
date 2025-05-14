

# routers/onboarding.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
import os
import httpx

from utils.security import get_current_user
from database import db  # conexión a Mongo o similar

router = APIRouter(prefix="/community", tags=["community"])

# ---------- MODELOS ----------
class OnboardingRequest(BaseModel):
    username: str
    profile_type: str  # Ej: "trader", "developer", "inversor"

class FoundingMemberRequest(BaseModel):
    user_id: str
    payment_proof: str  # URL o ID de Stripe
    discord_username: str

# ---------- GPT BOT DE ONBOARDING ----------
@router.post("/onboarding_gpt")
async def onboarding_gpt(req: OnboardingRequest):
    prompt = f"""
    Actúa como un mentor GPT para un nuevo usuario del sistema ZIMA. El perfil es: {req.profile_type}.
    Crea un tutorial de bienvenida, incluye links al canal de Discord, landing, blog y video demo.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        content = response.json()["choices"][0]["message"]["content"]

    return {"tutorial": content}

# ---------- REGISTRO DE FOUNDING MEMBERS ----------
@router.post("/founding_member")
async def register_founding_member(req: FoundingMemberRequest):
    count = await db.founding_members.count_documents({})
    if count >= 15:
        raise HTTPException(status_code=403, detail="Límite de Founding Members alcanzado")

    await db.founding_members.insert_one({
        "user_id": req.user_id,
        "payment_proof": req.payment_proof,
        "discord_username": req.discord_username,
        "benefits": {
            "access": "lifetime",
            "priority_support": True
        },
        "joined_at": datetime.utcnow()
    })

    return {"status": "registrado", "founding_member_number": count + 1}
