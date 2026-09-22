from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models import TipoUsuario, StatusComando, TipoComando


# ==========================================
# 1. SCHEMAS DE USUÁRIO (Motorista / Funcionário)
# ==========================================

# Schema base com campos comuns
class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100, example="Carlos Silva")
    email: EmailStr = Field(..., example="carlos.motorista@email.com")
    tipo: TipoUsuario = Field(..., example=TipoUsuario.CLIENTE)


# Schema para criação de usuário (recebe a senha no corpo da requisição)
class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6, max_length=50, example="senhaSegura123")


# Schema de resposta pública do usuário (oculta a senha criptografada por segurança)
class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    criado_em: datetime

    class Config:
        from_attributes = True  # Permite conversão direta do SQLAlchemy ORM para Pydantic


# ==========================================
# 2. SCHEMAS DE VEÍCULO
# ==========================================

class VeiculoBase(BaseModel):
    placa: str = Field(..., min_length=7, max_length=10, example="ABC1D23")
    modelo: str = Field(..., max_length=50, example="Volvo FH 540")
    marca: Optional[str] = Field(None, max_length=50, example="Volvo")
    ano: Optional[int] = Field(None, example=2023)


class VeiculoCreate(VeiculoBase):
    cliente_id: int = Field(..., example=1)  # ID do motorista proprietário


class VeiculoResponse(VeiculoBase):
    id: int
    cliente_id: int

    class Config:
        from_attributes = True


# ==========================================
# 3. SCHEMAS DE SOLICITAÇÃO DE COMANDO
# ==========================================

# Requisição que o Motorista faz pelo app/painel
class SolicitacaoComandoCreate(BaseModel):
    veiculo_id: int = Field(..., example=1)
    tipo_comando: TipoComando = Field(..., example=TipoComando.DESTRANCAR_BAU)


# Requisição que o Funcionário da central usa para aprovar/rejeitar
class AnaliseComandoUpdate(BaseModel):
    status: StatusComando = Field(..., example=StatusComando.APROVADO)
    observacao: Optional[str] = Field(None, example="Liberado após verificação por chamada")


# Resposta detalhada com os dados da solicitação do comando
class SolicitacaoComandoResponse(BaseModel):
    id: int
    veiculo_id: int
    motorista_id: int
    funcionario_id: Optional[int] = None
    tipo_comando: TipoComando
    status: StatusComando
    observacao: Optional[str] = None
    solicitado_em: datetime
    respondido_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# 4. SCHEMAS DE AUTENTICAÇÃO E TOKEN (JWT)
# ==========================================

class LoginSchema(BaseModel):
    email: EmailStr = Field(..., example="carlos.motorista@email.com")
    senha: str = Field(..., example="senhaSegura123")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    usuario_id: Optional[int] = None
    tipo: Optional[TipoUsuario] = None
