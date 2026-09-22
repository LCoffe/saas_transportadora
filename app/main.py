from typing import List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Importações dos módulos internos
from app.database import engine, Base, get_db
from app import models, schemas

from app.models import StatusComando 

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


# ==========================================
# ROTAS DE USUÁRIOS (Motoristas e Funcionários)
# ==========================================

@app.post(
    "/usuarios/", 
    response_model=schemas.UsuarioResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["Usuários"]
)
def criar_usuario(usuario: schemas.UsuarioCreate, criador_id: int, db: Session = Depends(get_db)):
    # Permitir cadastro inicial de Admin se o banco não tiver nenhum Admin ainda
    total_admins = db.query(models.UsuarioModel).filter(models.UsuarioModel.tipo == models.TipoUsuario.ADMIN).count()
    
    if total_admins > 0:
        if not criador_id:
            raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O parâmetro criador_id é obrigatório para cadastrar novos usuários."
                    )

        criador = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == criador_id).first()
        if not criador:
            raise HTTPException(status_code=401, detail="Usuário criador não encontrado.")
            
        # Regra 1: Funcionário só pode cadastrar Motorista (CLIENTE)
        if criador.tipo == models.TipoUsuario.FUNCIONARIO and usuario.tipo != models.TipoUsuario.CLIENTE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Funcionários só têm permissão para cadastrar motoristas/caminhoneiros."
            )
            
        # Regra 2: Apenas ADMIN pode cadastrar novos Funcionários ou Admins
        if criador.tipo == models.TipoUsuario.CLIENTE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Motoristas não possuem permissão para cadastrar usuários."
            )

    # Verificar se o e-mail já existe
    usuario_existente = db.query(models.UsuarioModel).filter(models.UsuarioModel.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado no sistema.")

    novo_usuario = models.UsuarioModel(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=usuario.senha,  # Mantida em texto puro
        tipo=usuario.tipo
    )
    
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@app.get("/usuarios/", response_model=List[schemas.UsuarioResponse], tags=["Usuários"])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.UsuarioModel).all()


# ==========================================
# ROTAS DE VEÍCULOS
# ==========================================

@app.post(
    "/veiculos/", 
    response_model=schemas.VeiculoResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["Veículos"]
)
def cadastrar_veiculo(veiculo: schemas.VeiculoCreate, db: Session = Depends(get_db)):
    # Verifica se a placa já existe
    db_veiculo = db.query(models.VeiculoModel).filter(models.VeiculoModel.placa == veiculo.placa).first()
    if db_veiculo:
        raise HTTPException(status_code=400, detail="Veículo com esta placa já cadastrado.")

    # Verifica se o cliente/proprietário informado existe
    proprietario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == veiculo.cliente_id).first()
    if not proprietario:
        raise HTTPException(status_code=404, detail="Motorista/Cliente informado não encontrado.")

    novo_veiculo = models.VeiculoModel(**veiculo.model_dump())
    db.add(novo_veiculo)
    db.commit()
    db.refresh(novo_veiculo)
    return novo_veiculo


# ==========================================
# ROTAS DE COMANDOS (Fluxo de Aprovação)
# ==========================================

# 1. Motorista Solicita o Comando
@app.post(
    "/comandos/solicitar", 
    response_model=schemas.SolicitacaoComandoResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["Comandos (Telemetria)"]
)
def solicitar_comando(
    motorista_id: int, 
    solicitacao: schemas.SolicitacaoComandoCreate, 
    db: Session = Depends(get_db)
):
    # Validar se o motorista existe
    motorista = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == motorista_id).first()
    if not motorista or motorista.tipo != models.TipoUsuario.CLIENTE:
        raise HTTPException(status_code=400, detail="Apenas motoristas cadastrados podem solicitar comandos.")

    nova_solicitacao = models.SolicitacaoComandoModel(
        veiculo_id=solicitacao.veiculo_id,
        motorista_id=motorista_id,
        tipo_comando=solicitacao.tipo_comando,
        status=models.StatusComando.PENDENTE
    )

    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)
    return nova_solicitacao


# 2. Central (Funcionário) Analisa e Aprova/Rejeita o Comando
@app.patch(
    "/comandos/{comando_id}/analisar", 
    response_model=schemas.SolicitacaoComandoResponse,
    tags=["Comandos (Telemetria)"]
)
def analisar_comando(
    comando_id: int, 
    funcionario_id: int, 
    analise: schemas.AnaliseComandoUpdate, 
    db: Session = Depends(get_db)
):
    # Validar funcionário da central
    funcionario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == funcionario_id).first()
    if not funcionario or funcionario.tipo != models.TipoUsuario.FUNCIONARIO:
        raise HTTPException(status_code=403, detail="Apenas funcionários da central podem aprovar/rejeitar comandos.")

    comando = db.query(models.SolicitacaoComandoModel).filter(models.SolicitacaoComandoModel.id == comando_id).first()
    if not comando:
        raise HTTPException(status_code=404, detail="Solicitação de comando não encontrada.")

    # Atualiza o status e grava a auditoria
    comando.status = analise.status
    comando.observacao = analise.observacao
    comando.funcionario_id = funcionario_id
    comando.respondido_em = datetime.utcnow()

    db.commit()
    db.refresh(comando)
    return comando


# 3. Listar Comandos Pendentes para a Central
@app.get(
    "/comandos/pendentes", 
    response_model=List[schemas.SolicitacaoComandoResponse],
    tags=["Comandos (Telemetria)"]
)
def listar_comandos_pendentes(db: Session = Depends(get_db)):
    return db.query(models.SolicitacaoComandoModel).filter(
        models.SolicitacaoComandoModel.status == models.StatusComando.PENDENTE
    ).all()


@app.get("/comandos/historico", response_model=List[schemas.SolicitacaoComandoResponse], tags=["Comandos"])
def obter_historico_comandos(db: Session = Depends(get_db)):
    return (
        db.query(models.SolicitacaoComandoModel)
        .filter(models.SolicitacaoComandoModel.status != models.StatusComando.PENDENTE)
        .order_by(models.SolicitacaoComandoModel.id.desc())
        .limit(5)
        .all()
    )