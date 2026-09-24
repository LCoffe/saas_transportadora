from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Importações dos módulos internos
from app.database import engine, Base
from app.routers import comandos, usuarios

# ==========================================
# Carga Inicial do Banco de Dados
# ==========================================
# Cria as tabelas no MySQL automaticamente com base nos modelos POO em models.py
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SaaS Telemetria & Monitoramento de Logística",
    description="API para solicitação e controle de comandos de veículos (trancar/destrancar baú, ignição).",
    version="1.0.0"
)

# Habilita permissões CORS para o frontend interagir com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção coloca-se a URL exata do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Registrar os Routers Modulares
# ==========================================
app.include_router(comandos.router)
app.include_router(usuarios.router)

# ==========================================
# Servir a interface Web do Frontend
# ==========================================
app.mount("/site", StaticFiles(directory="frontend", html=True), name="frontend")

# ==========================================
# ROTA INICIAL / HEALTH CHECK
# ==========================================
@app.get("/", tags=["Status"])
def health_check():
    return {
        "status": "online",
        "mensagem": "SaaS de Telemetria Operacional rodando com sucesso!",
        "timestamp": datetime.utcnow()
    }