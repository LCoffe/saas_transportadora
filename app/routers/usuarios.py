from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter(
    prefix="/usuarios",
    tags=["Utilizadores"]
)

@router.post("/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    usuario: schemas.UsuarioCreate, 
    criador_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    db_user = db.query(models.UsuarioModel).filter(models.UsuarioModel.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registado.")

    novo_usuario = models.UsuarioModel(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=usuario.senha,
        tipo=usuario.tipo
    )
    db.add(novo_usuario)
    db.flush()  # Gera o ID do novo utilizador no banco

    if usuario.tipo == models.TipoUsuario.CLIENTE and usuario.veiculo:
        novo_veiculo = models.VeiculoModel(
            placa=usuario.veiculo.placa.upper(),
            modelo=usuario.veiculo.modelo,
            marca=usuario.veiculo.marca,
            ano=usuario.veiculo.ano,
            cliente_id=novo_usuario.id
        )
        db.add(novo_veiculo)

    db.commit()
    db.refresh(novo_usuario)

    return novo_usuario

# 2. ROTA GET ADICIONADA (Para listar utilizadores e corrigir o erro 405)
@router.get("/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    """
    Retorna a lista completa de utilizadores do sistema.
    """
    return db.query(models.UsuarioModel).all()

@router.post("/login", response_model=schemas.LoginResponse, tags=["Autenticação"])
def login(dados: schemas.LoginSchema, db: Session = Depends(get_db)):
    # 1. Busca o usuário pelo e-mail
    usuario = db.query(models.UsuarioModel).filter(or_(models.UsuarioModel.email == dados.login, models.UsuarioModel.nome == dados.login)).first()
    
    # 2. Se o usuário não existir, rejeita com 401
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail/Login ou senha incorretos."
        )

    if usuario.senha_hash != dados.senha:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail/Login ou senha incorretos."
        )

    # (Se ainda não estiver gerando JWT real, pode retornar a estrutura estática do schema Token:)
    return {
        "access_token": f"token_{usuario.id}",
        "token_type": "bearer",
        "usuario_id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "tipo": usuario.tipo
    }