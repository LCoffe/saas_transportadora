from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.schemas import UsuarioResponse, UsuarioUpdate

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

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(usuario_id: int, dados_atualizacao: UsuarioUpdate, usuario_logado_id: int, usuario_logado_tipo: str, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um usuário específico.
    """
    usuario_db = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == usuario_id).first()
    
    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuário não encontrado."
        )

    # validações de permissão com base no tipo de usuário logado
    if usuario_logado_tipo == "CLIENTE":
        # Cliente só pode mexer nos próprios dados e NÃO pode alterar seu tipo para ADMIN/FUNCIONARIO
        if usuario_logado_id != usuario_id:
            raise HTTPException(status_code=403, detail="Acesso negado: Você só pode editar seus próprios dados.")
        if dados_atualizacao.tipo and dados_atualizacao.tipo != models.TipoUsuario.CLIENTE:
            raise HTTPException(status_code=403, detail="Clientes não podem alterar seu próprio tipo de perfil.")

    elif usuario_logado_tipo == "FUNCIONARIO":
        # Funcionário pode alterar seus próprios dados OU dados de clientes (caminhoneiros)
        if usuario_logado_id != usuario_id and usuario_db.tipo != models.TipoUsuario.CLIENTE:
            raise HTTPException(status_code=403, detail="Funcionários só podem editar seus próprios dados ou de caminhoneiros (clientes).")

    # Pega apenas os campos enviados na requisição
    dados_dict = dados_atualizacao.dict(exclude_unset=True)
    dados_veiculo = dados_dict.pop("veiculo", None) # pega os dados do veículo, se houver, e remove do dict principal
    
    # Tratamento especial para o campo 'senha': 
    if "senha" in dados_dict:
        senha = dados_dict.pop("senha")
        usuario_db.senha_hash = senha
    
    # Atualiza os demais campos (nome, email, tipo, ativo) dinamicamente
    for chave, valor in dados_dict.items():
        setattr(usuario_db, chave, valor)

    if dados_veiculo is not None:
        # Verifica se o usuário já possui um veículo cadastrado
        veiculo_db = db.query(models.VeiculoModel).filter(models.VeiculoModel.cliente_id == usuario_id).first()
        
        if veiculo_db:
            # Se já tem, atualiza apenas os campos enviados do veículo
            for v_chave, v_valor in dados_veiculo.items():
                if v_valor is not None:
                    setattr(veiculo_db, v_chave, v_valor)
        else:
            # Se não tem veículo e enviou os dados, cria um novo vinculado a este usuário
            novo_veiculo = models.VeiculoModel(
                cliente_id=usuario_id,
                placa=dados_veiculo.get("placa"),
                modelo=dados_veiculo.get("modelo"),
                marca=dados_veiculo.get("marca"),
                ano=dados_veiculo.get("ano")
            )
            db.add(novo_veiculo)

    # 6. Salva todas as alterações no banco de dados
    db.commit()
    db.refresh(usuario_db)
    
    return usuario_db
    
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """
    Exclui um usuário específico do sistema.
    """
    # Busca o usuário no banco de dados
    usuario_db = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == usuario_id).first()
    
    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuário não encontrado."
        )
    
    db.delete(usuario_db)
    db.commit()
    return None


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