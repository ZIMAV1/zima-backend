
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from utils.security import get_current_user
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

# Simulada base de datos de usuarios (en producción usar DB real)
admin_user_db: List[dict] = []

# Modelo de usuario para administración
class AdminUser(BaseModel):
    id: str
    email: str
    plan: str
    role: str
    created_at: datetime

class AdminUpdateUser(BaseModel):
    plan: Optional[str]
    role: Optional[str]

# Middleware: solo admins pueden acceder
async def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="⛔ Solo admins pueden acceder a esta ruta.")
    return user

# Endpoint: listar usuarios
@router.get("/users", response_model=List[AdminUser])
async def list_users(current_user: User = Depends(require_admin)):
    return admin_user_db

# Endpoint: actualizar plan/rol de un usuario
@router.put("/users/{user_id}")
async def update_user(user_id: str, update: AdminUpdateUser, current_user: User = Depends(require_admin)):
    for user in admin_user_db:
        if user["id"] == user_id:
            if update.plan:
                user["plan"] = update.plan
            if update.role:
                user["role"] = update.role
            return {"status": "ok", "message": "✅ Usuario actualizado"}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

# Endpoint: eliminar usuario
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(require_admin)):
    global admin_user_db
    admin_user_db = [u for u in admin_user_db if u["id"] != user_id]
    return {"status": "ok", "message": f"✅ Usuario {user_id} eliminado"}

# Endpoint: crear usuario desde panel
@router.post("/users")
async def create_user(email: str, plan: str = "freemium", role: str = "user", current_user: User = Depends(require_admin)):
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "plan": plan,
        "role": role,
        "created_at": datetime.utcnow()
    }
    admin_user_db.append(new_user)
    return {"status": "ok", "user": new_user}


# routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import json
import uuid

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

DATA_PATH = "data"
USERS_PATH = os.path.join(DATA_PATH, "users.json")
LICENSES_PATH = os.path.join(DATA_PATH, "licenses.json")

os.makedirs(DATA_PATH, exist_ok=True)

# ===============================
# Modelos
# ===============================
class UserRecord(BaseModel):
    id: str
    email: str
    plan: str
    role: str
    created_at: str

class LicenseRecord(BaseModel):
    id: str
    api_key: str
    owner_email: str
    plan: str
    active: bool
    created_at: str

# ===============================
# Helpers JSON
# ===============================
def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ===============================
# ENDPOINT: Obtener usuarios registrados
# ===============================
@router.get("/users", response_model=List[UserRecord])
async def list_users():
    return load_json(USERS_PATH)

# ===============================
# ENDPOINT: Agregar usuario manualmente
# ===============================
@router.post("/users/add")
async def add_user(email: str = Form(...), plan: str = Form("freemium"), role: str = Form("user")):
    users = load_json(USERS_PATH)
    new_user = UserRecord(
        id=str(uuid.uuid4()),
        email=email,
        plan=plan,
        role=role,
        created_at=datetime.utcnow().isoformat()
    )
    users.append(new_user.dict())
    save_json(USERS_PATH, users)
    return {"message": "✅ Usuario agregado", "user_id": new_user.id}

# ===============================
# ENDPOINT: Ver licencias activas
# ===============================
@router.get("/licenses", response_model=List[LicenseRecord])
async def list_licenses():
    return load_json(LICENSES_PATH)

# ===============================
# ENDPOINT: Crear nueva licencia API
# ===============================
@router.post("/licenses/create")
async def create_license(owner_email: str = Form(...), plan: str = Form("freemium")):
    licenses = load_json(LICENSES_PATH)
    new_license = LicenseRecord(
        id=str(uuid.uuid4()),
        api_key=str(uuid.uuid4()),
        owner_email=owner_email,
        plan=plan,
        active=True,
        created_at=datetime.utcnow().isoformat()
    )
    licenses.append(new_license.dict())
    save_json(LICENSES_PATH, licenses)
    return {
        "message": "✅ Licencia creada",
        "api_key": new_license.api_key
    }

# ===============================
# ENDPOINT: Revocar licencia por ID
# ===============================
@router.post("/licenses/revoke")
async def revoke_license(license_id: str = Form(...)):
    licenses = load_json(LICENSES_PATH)
    found = False
    for lic in licenses:
        if lic["id"] == license_id:
            lic["active"] = False
            found = True
    save_json(LICENSES_PATH, licenses)
    if found:
        return {"message": "🔒 Licencia revocada"}
    raise HTTPException(status_code=404, detail="Licencia no encontrada")


# routers/admin.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from database import db
from utils.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

# ===============================
# Modelos
# ===============================
class UpdateUserPlan(BaseModel):
    user_email: str
    new_plan: str  # freemium | pro | institutional

class LicenseToken(BaseModel):
    token_id: str
    issued_to: str
    expires_at: Optional[datetime]
    scopes: List[str]

# ===============================
# Ver todos los usuarios registrados
# ===============================
@router.get("/users")
async def get_all_users(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    users = await db.users.find().to_list(100)
    return users

# ===============================
# Cambiar plan de un usuario
# ===============================
@router.post("/update_plan")
async def update_user_plan(data: UpdateUserPlan, user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    result = await db.users.update_one(
        {"email": data.user_email},
        {"$set": {"plan": data.new_plan}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": f"✅ Plan actualizado a {data.new_plan}"}

# ===============================
# Crear nueva licencia
# ===============================
@router.post("/licenses/create")
async def create_license(lic: LicenseToken, user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    await db.licenses.insert_one({
        "token_id": lic.token_id,
        "issued_to": lic.issued_to,
        "scopes": lic.scopes,
        "expires_at": lic.expires_at,
        "created_at": datetime.utcnow()
    })

    return {"status": "ok", "message": "✅ Licencia creada"}

# ===============================
# Ver licencias activas
# ===============================
@router.get("/licenses")
async def get_licenses(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return await db.licenses.find().to_list(100)


# routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from datetime import datetime
from database import db
from utils.security import get_current_user
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

# =============================
# Modelos
# =============================
class UserSummary(BaseModel):
    id: str
    email: str
    role: str
    plan: str
    created_at: datetime

class UpdateUserRole(BaseModel):
    user_id: str
    new_role: str

class UpdateUserPlan(BaseModel):
    user_id: str
    new_plan: str

# =============================
# Solo para admins
# =============================
def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="⛔ Solo administradores autorizados")
    return user

# =============================
# Obtener todos los usuarios
# =============================
@router.get("/users", response_model=List[UserSummary])
async def get_all_users(admin=Depends(require_admin)):
    users = await db.users.find().to_list(1000)
    return [UserSummary(**u) for u in users]

# =============================
# Actualizar rol de usuario
# =============================
@router.post("/user/role")
async def update_user_role(data: UpdateUserRole, admin=Depends(require_admin)):
    updated = await db.users.update_one({"_id": data.user_id}, {"$set": {"role": data.new_role}})
    if updated.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin cambios")
    return {"status": "✅ Rol actualizado"}

# =============================
# Actualizar plan de usuario
# =============================
@router.post("/user/plan")
async def update_user_plan(data: UpdateUserPlan, admin=Depends(require_admin)):
    updated = await db.users.update_one({"_id": data.user_id}, {"$set": {"plan": data.new_plan}})
    if updated.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin cambios")
    return {"status": "✅ Plan actualizado"}

# =============================
# Dashboard de administración
# =============================
@router.get("/dashboard")
async def admin_dashboard(admin=Depends(require_admin)):
    total_users = await db.users.count_documents({})
    premium = await db.users.count_documents({"plan": "pro"})
    freemium = await db.users.count_documents({"plan": "freemium"})

    return {
        "total_users": total_users,
        "premium_users": premium,
        "freemium_users": freemium,
        "timestamp": datetime.utcnow()
    }


# routers/admin.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List
from database import db
from utils.security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================
# Modelos de datos
# ============================
class UserSummary(BaseModel):
    id: str
    email: str
    role: str
    plan: str
    created_at: datetime

class PlanUpdateRequest(BaseModel):
    user_id: str
    new_plan: str

class RoleUpdateRequest(BaseModel):
    user_id: str
    new_role: str

# ============================
# Middleware: solo admin
# ============================
def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return user

# ============================
# Endpoint: listar todos los usuarios
# ============================
@router.get("/users", response_model=List[UserSummary])
async def list_users(admin=Depends(require_admin)):
    users = await db.users.find().to_list(1000)
    return [
        UserSummary(
            id=str(u["_id"]),
            email=u["email"],
            role=u.get("role", "user"),
            plan=u.get("plan", "free"),
            created_at=u.get("created_at", datetime.utcnow())
        )
        for u in users
    ]

# ============================
# Endpoint: actualizar plan de usuario
# ============================
@router.post("/update/plan")
async def update_plan(req: PlanUpdateRequest, admin=Depends(require_admin)):
    result = await db.users.update_one(
        {"_id": req.user_id},
        {"$set": {"plan": req.new_plan}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin cambios")
    return {"message": f"✅ Plan actualizado a {req.new_plan}"}

# ============================
# Endpoint: actualizar rol de usuario
# ============================
@router.post("/update/role")
async def update_role(req: RoleUpdateRequest, admin=Depends(require_admin)):
    result = await db.users.update_one(
        {"_id": req.user_id},
        {"$set": {"role": req.new_role}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin cambios")
    return {"message": f"✅ Rol actualizado a {req.new_role}"}


# routers/admin.py

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List
import stripe
import os
from models.user import User
from utils.security import get_db

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# === ENDPOINT: Listar todos los usuarios registrados ===
@router.get("/users", response_model=List[dict])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{
        "id": u.id,
        "email": u.email,
        "plan": u.plan,
        "role": u.role
    } for u in users]

# === ENDPOINT: Forzar upgrade manual de plan ===
@router.post("/upgrade")
def upgrade_user(email: str, new_plan: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.plan = new_plan
    db.commit()
    return {"message": f"✅ Plan actualizado a '{new_plan}' para {email}"}

# === WEBHOOK STRIPE para upgrades automáticos ===
@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "customer.subscription.created":
        email = event["data"]["object"].get("customer_email")
        plan_id = event["data"]["object"]["items"]["data"][0]["price"]["nickname"]
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = plan_id.lower()
            db.commit()

    elif event["type"] == "customer.subscription.deleted":
        email = event["data"]["object"].get("customer_email")
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = "free"
            db.commit()

    return {"status": "✅ Webhook recibido y procesado"}
