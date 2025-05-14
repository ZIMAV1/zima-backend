# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Importar routers
from routers.auth import router as auth_router
from routers.dao import router as dao_router
from routers.onboarding import router as onboarding_router
from routers.marketplace import router as marketplace_router
from routers.metrics import router as metrics_router
from routers.admin import router as admin_router
from routers.licenses import router as licenses_router

# Configuración base
app = FastAPI(
    title="ZIMA Backend API",
    version="1.0.0",
    description="Sistema completo de backend para ZIMA SaaS"
)

# CORS: permitir frontend en Vercel o localhost
origins = [
    "http://localhost:3000",
    "https://zima-frontend.vercel.app",
    "https://zima.ia"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth_router, prefix="/auth")
app.include_router(dao_router, prefix="/dao")
app.include_router(onboarding_router, prefix="/community")
app.include_router(marketplace_router, prefix="/marketplace")
app.include_router(metrics_router, prefix="/metrics")
app.include_router(admin_router, prefix="/admin")
app.include_router(licenses_router, prefix="/licenses")

# Healthcheck
@app.get("/")
def read_root():
    return {"status": "✅ ZIMA backend online", "version": "1.0.0"}

# Ejecución local
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
