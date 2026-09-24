from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db

# Instância do APIRouter para gerir as rotas de telemetria
router = APIRouter(
    prefix="/comandos",
    tags=["Comandos (Telemetria)"]
)

# ==============================================================================
# 1. LISTAR COMANDOS DA FILA (Filtro Dinâmico por Perfil)
# ==============================================================================
@router.get("/", response_model=List[schemas.SolicitacaoComandoResponse])
def listar_comandos(
    usuario_id: Optional[int] = None, 
    tipo_usuario: Optional[models.TipoUsuario] = None, 
    db: Session = Depends(get_db)
):
    """
    Lista os comandos da fila de acordo com o perfil:
    - CLIENTE (Motorista): Vê apenas as suas próprias solicitações.
    - FUNCIONARIO: Vê as solicitações pendentes para análise.
    - ADMIN ou Sem Parâmetros: Vê todas as solicitações da fila.
    """
    query = db.query(models.SolicitacaoComandoModel)\
              .options(
                  joinedload(models.SolicitacaoComandoModel.veiculo),
                  joinedload(models.SolicitacaoComandoModel.motorista)
              )

    if tipo_usuario == models.TipoUsuario.CLIENTE and usuario_id:
        query = query.filter(models.SolicitacaoComandoModel.motorista_id == usuario_id, models.SolicitacaoComandoModel.status == models.StatusComando.PENDENTE)

    # Se tipo_usuario for ADMIN ou Funcionário, retorna todos os comandos da fila
    return query.filter(models.SolicitacaoComandoModel.status == models.StatusComando.PENDENTE)\
                .order_by(models.SolicitacaoComandoModel.id.desc()).all()


# ==============================================================================
# 2. MOTORISTA SOLICITA COMANDO (Vínculo Automático de Veículo)
# ==============================================================================
@router.post(
    "/solicitar", 
    response_model=schemas.SolicitacaoComandoResponse, 
    status_code=status.HTTP_201_CREATED
)
def solicitar_comando(
    motorista_id: int, 
    solicitacao: schemas.SolicitacaoComandoCreate, 
    db: Session = Depends(get_db)
):
    """
    Registra um novo comando vinculando automaticamente o veículo cadastrado do motorista.
    """
    # 1. Validar se o motorista existe e se é CLIENTE
    motorista = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == motorista_id).first()
    if not motorista or motorista.tipo != models.TipoUsuario.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Apenas motoristas cadastrados podem solicitar comandos."
        )

    # 2. Busca automaticamente o veículo associado ao motorista
    veiculo = db.query(models.VeiculoModel).filter(models.VeiculoModel.cliente_id == motorista_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="O motorista não possui nenhum veículo cadastrado no sistema."
        )
    
    # 3. Cria a solicitação pendente
    nova_solicitacao = models.SolicitacaoComandoModel(
        veiculo_id=veiculo.id,
        motorista_id=motorista_id,
        tipo_comando=solicitacao.tipo_comando,
        status=models.StatusComando.PENDENTE
    )

    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)
    return nova_solicitacao


# ==============================================================================
# 3. CENTRAL ANALISA E APROVA / REJEITA COMANDO
# ==============================================================================
@router.patch("/{comando_id}/analisar", response_model=schemas.SolicitacaoComandoResponse)
def analisar_comando(
    comando_id: int, 
    funcionario_id: int, 
    analise: schemas.AnaliseComandoUpdate, 
    db: Session = Depends(get_db)
):
    """
    Muda o status do comando (APROVADO/REJEITADO) com validação de perfil de operador.
    """
    # 1. Validar operador da central
    funcionario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == funcionario_id).first()
    if not funcionario or funcionario.tipo == models.TipoUsuario.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Apenas funcionários da central podem aprovar ou rejeitar comandos."
        )

    # 2. Buscar o comando
    comando = db.query(models.SolicitacaoComandoModel).filter(models.SolicitacaoComandoModel.id == comando_id).first()
    if not comando:
        raise HTTPException(status_code=404, detail="Solicitação de comando não encontrada.")

    # 3. Atualizar auditoria e estado
    comando.status = analise.status
    comando.observacao = analise.observacao
    comando.funcionario_id = funcionario_id
    comando.respondido_em = datetime.utcnow()

    db.commit()
    db.refresh(comando)
    return comando


# ==============================================================================
# 4. HISTÓRICO DE COMANDOS PROCESSADOS (Aprovados / Rejeitados)
# ==============================================================================
@router.get("/historico", response_model=List[schemas.SolicitacaoComandoResponse])
def obter_historico_comandos(
    usuario_id: Optional[int] = None, 
    tipo_usuario: Optional[models.TipoUsuario] = None, 
    db: Session = Depends(get_db)
):
    """
    Exibe histórico de comandos finalizados (não pendentes):
    - CLIENTE (Motorista): Vê as decisões sobre os seus próprios comandos.
    - FUNCIONARIO: Vê as decisões tomadas por ele próprio.
    - ADMIN ou Sem Parâmetros: Vê todas as decisões tomadas no sistema.
    """
    query = db.query(models.SolicitacaoComandoModel)\
              .options(
                  joinedload(models.SolicitacaoComandoModel.veiculo),
                  joinedload(models.SolicitacaoComandoModel.motorista)
              )\
              .filter(models.SolicitacaoComandoModel.status != models.StatusComando.PENDENTE)

    if tipo_usuario == models.TipoUsuario.CLIENTE and usuario_id:
        query = query.filter(models.SolicitacaoComandoModel.motorista_id == usuario_id)

    elif tipo_usuario == models.TipoUsuario.FUNCIONARIO and usuario_id:
        query = query.filter(models.SolicitacaoComandoModel.funcionario_id == usuario_id)

    elif tipo_usuario == models.TipoUsuario.ADMIN:
        # Se ADMIN, traz o histórico global
        pass

    # Se ADMIN ou sem parâmetros, traz o histórico global
    return query.order_by(models.SolicitacaoComandoModel.id.desc()).all()