from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, time
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/encomendas", tags=["Encomendas"])

def gerar_serial_diario(db: Session) -> str:
    hoje = datetime.utcnow().date()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)

    total_hoje = db.query(models.EncomendaModel).filter(
        models.EncomendaModel.criado_em >= inicio_dia,
        models.EncomendaModel.criado_em <= fim_dia
    ).count()

    numero_pedido = total_hoje + 1
    prefixo_data = hoje.strftime("%Y%m%d")
    return f"{prefixo_data}-{numero_pedido:03d}"

@router.post("/", response_model=schemas.EncomendaResponse, status_code=status.HTTP_201_CREATED)
def criar_encomenda(payload: schemas.CriarEncomendaSchema, db: Session = Depends(get_db)):
    serial_gerado = gerar_serial_diario(db)

    # 1. Cria a Encomenda
    nova_encomenda = models.EncomendaModel(
        serial=serial_gerado,
        descricao=payload.descricao
    )
    db.add(nova_encomenda)
    db.flush()

    # 2. Cria a Rota com os campos de endereço separados
    nova_rota = models.RotaModel(
        serial=serial_gerado,
        rua=payload.rua,
        numero=payload.numero,
        complemento=payload.complemento,
        bairro=payload.bairro,
        cidade=payload.cidade,
        estado=payload.estado.upper(),
        encomenda_id=nova_encomenda.id
    )
    db.add(nova_rota)

    db.commit()
    db.refresh(nova_encomenda)

    return {
        "id": nova_encomenda.id,
        "serial": nova_encomenda.serial,
        "descricao": nova_encomenda.descricao,
        "rua": nova_rota.rua,
        "numero": nova_rota.numero,
        "complemento": nova_rota.complemento,
        "bairro": nova_rota.bairro,
        "cidade": nova_rota.cidade,
        "estado": nova_rota.estado,
        "criado_em": nova_encomenda.criado_em
    }