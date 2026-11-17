from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/rotas", tags=["Rotas"])

@router.get("/disponiveis", response_model=List[schemas.RotaDisponivelResponse])
def listar_rotas_disponiveis(db: Session = Depends(get_db)):
    """Retorna todas as rotas que ainda não foram aceitas por nenhum motorista."""
    return (
        db.query(models.RotaModel)
        .options(joinedload(models.RotaModel.encomenda))
        .filter(models.RotaModel.status == "DISPONIVEL")
        .order_by(models.RotaModel.id.asc())
        .all()
    )

@router.post("/{rota_id}/aceitar", response_model=schemas.RotaIniciadaResponse, status_code=status.HTTP_201_CREATED)
def aceitar_rota(rota_id: int, payload: schemas.AceitarRotaSchema, db: Session = Depends(get_db)):
    # 1. Valida se o usuário existe e se é do tipo CLIENTE (motorista)
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == payload.motorista_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    if usuario.tipo != models.TipoUsuario.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com perfil de CLIENTE (motorista) podem aceitar rotas."
        )

    # 2. Valida a disponibilidade da rota
    rota = db.query(models.RotaModel).filter(models.RotaModel.id == rota_id).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada.")
    if rota.status != "DISPONIVEL":
        raise HTTPException(status_code=400, detail="Esta rota já foi aceita por outro motorista.")

    # 3. Atualiza status e cria o registro em rotas_iniciadas
    rota.status = "ACEITA"

    nova_rota_iniciada = models.RotaIniciadaModel(
        serial=rota.serial,
        rota_id=rota.id,
        encomenda_id=rota.encomenda_id,
        motorista_id=payload.motorista_id,
        status="EM_ANDAMENTO"
    )
    db.add(nova_rota_iniciada)
    db.commit()
    db.refresh(nova_rota_iniciada)

    return nova_rota_iniciada

@router.get("/minhas")
def listar_minhas_rotas(usuario_id: int, tipo_usuario: str, db: Session = Depends(get_db)):
    """
    Lista as rotas em andamento. 
    Se for CLIENTE, filtra apenas as rotas aceitas por ele.
    Se for ADMIN ou FUNCIONARIO, lista todas as rotas em andamento.
    """
    query = (
        db.query(models.RotaIniciadaModel)
        .options(
            joinedload(models.RotaIniciadaModel.rota),
            joinedload(models.RotaIniciadaModel.encomenda),
            joinedload(models.RotaIniciadaModel.motorista)
        )
    )

    if tipo_usuario == "CLIENTE":
        query = query.filter(models.RotaIniciadaModel.motorista_id == usuario_id)

    rotas_iniciadas = query.order_by(models.RotaIniciadaModel.id.desc()).all()

    resultado = []
    for item in rotas_iniciadas:
        resultado.append({
            "id": item.id,
            "serial": item.serial,
            "status": item.status,
            "iniciada_em": item.iniciada_em,
            "motorista_id": item.motorista_id,
            "motorista_nome": item.motorista.nome if item.motorista else f"Motorista #{item.motorista_id}",
            "descricao": item.encomenda.descricao if item.encomenda else "Sem descrição",
            "rua": item.rota.rua if item.rota else "",
            "numero": item.rota.numero if item.rota else "",
            "complemento": item.rota.complemento if item.rota else None,
            "bairro": item.rota.bairro if item.rota else "",
            "cidade": item.rota.cidade if item.rota else "",
            "estado": item.rota.estado if item.rota else "",
        })

    return resultado

from pydantic import BaseModel

# Schema auxiliar para receber os dados enviados pelo frontend
class AtualizarMotoristaSchema(BaseModel):
    novo_motorista_id: int
    usuario_logado_tipo: str

@router.put("/iniciadas/{rota_id}/motorista")
def alterar_motorista_rota(rota_id: int, payload: AtualizarMotoristaSchema, db: Session = Depends(get_db)):
    # 1. Busca a rota iniciada pelo ID
    rota_iniciada = db.query(models.RotaIniciadaModel).filter(models.RotaIniciadaModel.id == rota_id).first()
    if not rota_iniciada:
        raise HTTPException(status_code=404, detail="Rota iniciada não encontrada.")

    # 2. Verifica se o novo motorista existe e se é do tipo CLIENTE
    novo_motorista = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == payload.novo_motorista_id).first()
    if not novo_motorista:
        raise HTTPException(status_code=404, detail="Novo motorista não encontrado.")
    
    if novo_motorista.tipo != models.TipoUsuario.CLIENTE:
        raise HTTPException(status_code=400, detail="O usuário selecionado não é um motorista válido.")

    # 3. Atualiza o motorista responsável
    rota_iniciada.motorista_id = payload.novo_motorista_id
    db.commit()
    db.refresh(rota_iniciada)

    return {"message": "Motorista da rota alterado com sucesso!"}