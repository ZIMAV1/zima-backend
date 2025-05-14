
# routers/licenses.py

from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import List, Dict
import uuid
import json
import os

router = APIRouter()

LICENSE_DB_PATH = "data/licenses.json"
os.makedirs("data", exist_ok=True)

# ===============================
# Modelos
# ===============================
class License(BaseModel):
    id: str
    partner_name: str
    api_key: str
    active: bool = True

# ===============================
# Helpers de archivo JSON
# ===============================
def load_licenses() -> List[Dict]:
    if not os.path.exists(LICENSE_DB_PATH):
        return []
    with open(LICENSE_DB_PATH, "r") as f:
        return json.load(f)

def save_licenses(data: List[Dict]):
    with open(LICENSE_DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ===============================
# ENDPOINT: Crear nueva licencia
# ===============================
@router.post("/licenses/create", response_model=License)
async def create_license(partner_name: str = Form(...)):
    licenses = load_licenses()
    new_license = License(
        id=str(uuid.uuid4()),
        partner_name=partner_name,
        api_key=str(uuid.uuid4()).replace("-", "")
    )
    licenses.append(new_license.dict())
    save_licenses(licenses)
    return new_license

# ===============================
# ENDPOINT: Listar licencias
# ===============================
@router.get("/licenses", response_model=List[License])
async def list_licenses():
    return load_licenses()

# ===============================
# ENDPOINT: Revocar licencia
# ===============================
@router.post("/licenses/revoke")
async def revoke_license(license_id: str = Form(...)):
    licenses = load_licenses()
    for lic in licenses:
        if lic["id"] == license_id:
            lic["active"] = False
            save_licenses(licenses)
            return {"status": "revocada"}
    raise HTTPException(status_code=404, detail="Licencia no encontrada")

# ===============================
# Función para validar API Key
# ===============================
def get_partner_from_key(api_key: str) -> str:
    licenses = load_licenses()
    for lic in licenses:
        if lic["api_key"] == api_key and lic["active"]:
            return lic["partner_name"]
    return None

# routers/licenses.py

from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import uuid
import json

router = APIRouter(prefix="/licenses", tags=["Licenses"])

LICENSES_PATH = "data/licenses.json"
os.makedirs("data", exist_ok=True)

# ==============================
# Modelo de Licencia
# ==============================
class LicenseModel(BaseModel):
    id: str
    api_key: str
    owner_email: str
    plan: str
    active: bool
    created_at: str

# ==============================
# Helpers de JSON
# ==============================
def load_licenses() -> List[dict]:
    if not os.path.exists(LICENSES_PATH):
        return []
    with open(LICENSES_PATH, "r") as f:
        return json.load(f)

def save_licenses(licenses: List[dict]):
    with open(LICENSES_PATH, "w") as f:
        json.dump(licenses, f, indent=2)

# ==============================
# Crear nueva licencia
# ==============================
@router.post("/create", response_model=LicenseModel)
async def create_license(owner_email: str = Form(...), plan: str = Form("freemium")):
    licenses = load_licenses()
    new_license = {
        "id": str(uuid.uuid4()),
        "api_key": str(uuid.uuid4()),
        "owner_email": owner_email,
        "plan": plan,
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    licenses.append(new_license)
    save_licenses(licenses)
    return new_license

# ==============================
# Listar todas las licencias
# ==============================
@router.get("/", response_model=List[LicenseModel])
async def list_all_licenses():
    return load_licenses()

# ==============================
# Verificar licencia por API Key
# ==============================
@router.get("/verify/{api_key}")
async def verify_license(api_key: str):
    licenses = load_licenses()
    for lic in licenses:
        if lic["api_key"] == api_key and lic["active"]:
            return {
                "status": "valid",
                "owner_email": lic["owner_email"],
                "plan": lic["plan"]
            }
    raise HTTPException(status_code=403, detail="API Key inválida o revocada.")

# ==============================
# Revocar licencia
# ==============================
@router.post("/revoke")
async def revoke_license(license_id: str = Form(...)):
    licenses = load_licenses()
    for lic in licenses:
        if lic["id"] == license_id:
            lic["active"] = False
            save_licenses(licenses)
            return {"message": "🔒 Licencia revocada correctamente."}
    raise HTTPException(status_code=404, detail="Licencia no encontrada.")


# routers/licenses.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from database import db
from utils.security import get_current_user

router = APIRouter(prefix="/licenses", tags=["Licenses"])

# ============================
# Modelos
# ============================
class LicenseCreate(BaseModel):
    issued_to: str
    scopes: List[str]
    expires_in_days: Optional[int] = 30

class LicenseOut(BaseModel):
    token_id: str
    issued_to: str
    scopes: List[str]
    created_at: datetime
    expires_at: datetime

# ============================
# Crear una nueva licencia
# ============================
@router.post("/create", response_model=LicenseOut)
async def create_license(data: LicenseCreate, user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    token_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=data.expires_in_days)

    license_doc = {
        "token_id": token_id,
        "issued_to": data.issued_to,
        "scopes": data.scopes,
        "created_at": created_at,
        "expires_at": expires_at
    }

    await db.licenses.insert_one(license_doc)

    return LicenseOut(**license_doc)

# ============================
# Listar todas las licencias
# ============================
@router.get("/", response_model=List[LicenseOut])
async def list_licenses(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    licenses = await db.licenses.find().to_list(100)
    return [LicenseOut(**l) for l in licenses]

# ============================
# Validar token
# ============================
@router.get("/validate/{token_id}")
async def validate_token(token_id: str):
    lic = await db.licenses.find_one({"token_id": token_id})
    if not lic:
        raise HTTPException(status_code=404, detail="Licencia no encontrada")

    if lic["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Licencia expirada")

    return {
        "token_id": lic["token_id"],
        "issued_to": lic["issued_to"],
        "scopes": lic["scopes"],
        "status": "valid"
    }


# routers/licenses.py

from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Dict, List
import uuid
import json
import os
import redis
from datetime import datetime

router = APIRouter(prefix="/api/licenses", tags=["Licenses"])

# Inicializar Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Path simulado (en producción usar DB real)
PARTNER_KEYS_FILE = "config/partner_keys.json"
os.makedirs("config", exist_ok=True)
if not os.path.exists(PARTNER_KEYS_FILE):
    with open(PARTNER_KEYS_FILE, "w") as f:
        json.dump({"partners": {}}, f)

# === Modelos ===
class LicenseRequest(BaseModel):
    partner_name: str
    stripe_customer_id: str

class License(BaseModel):
    api_key: str
    partner_name: str
    stripe_customer_id: str
    created_at: str

# === Cargar y guardar desde archivo json ===
def load_keys() -> Dict:
    with open(PARTNER_KEYS_FILE) as f:
        return json.load(f)

def save_keys(data: Dict):
    with open(PARTNER_KEYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# === ENDPOINT: Generar nueva API Key ===
@router.post("/generate", response_model=License)
def generate_api_key(req: LicenseRequest):
    data = load_keys()
    if req.partner_name in data["partners"]:
        raise HTTPException(status_code=400, detail="Partner ya existe")

    new_key = str(uuid.uuid4())
    record = {
        "api_key": new_key,
        "stripe_customer_id": req.stripe_customer_id,
        "created_at": datetime.utcnow().isoformat()
    }
    data["partners"][req.partner_name] = record
    save_keys(data)

    return {
        "api_key": new_key,
        "partner_name": req.partner_name,
        "stripe_customer_id": req.stripe_customer_id,
        "created_at": record["created_at"]
    }

# === ENDPOINT: Listar claves ===
@router.get("/list", response_model=Dict)
def list_keys():
    return load_keys()["partners"]

# === ENDPOINT: Revocar API Key ===
@router.delete("/revoke")
def revoke_key(partner_name: str = Form(...)):
    data = load_keys()
    if partner_name not in data["partners"]:
        raise HTTPException(status_code=404, detail="Partner no encontrado")

    del data["partners"][partner_name]
    save_keys(data)
    return {"status": "revocado", "partner": partner_name}

