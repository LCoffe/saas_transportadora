from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models import TipoUsuario, StatusComando, TipoComando


# ==========================================
# 1. SCHEMAS DE VEÍCULO
# ==========================================

class VeiculoBase(BaseModel):
    placa: str = Field(..., min_length=7, max_length=10, example="ABC1D23")
    modelo: str = Field(..., max_length=50, example="Volvo FH 540")
    marca: Optional[str] = Field(None, max_length=50, example="Volvo")
    ano: Optional[int] = Field(None, example=2023)


class VeiculoCreate(VeiculoBase):
    cliente_id: int = Field(..., example=1)  # ID do motorista proprietário

class VeiculoAninhadoCreate(VeiculoBase):
    placa: str
    modelo: str
    marca: Optional[str] = None
    ano: Optional[int] = None

class VeiculoResponse(VeiculoBase):
    id: int
    cliente_id: int

    class Config:
        from_attributes = True

class VeiculoResumoResponse(BaseModel):
    id: int
    placa: str
    modelo: str

    class Config:
        from_attributes = True

# ==========================================
# 2. SCHEMAS DE USUÁRIO (Motorista / Funcionário)
# ==========================================

# Schema base com campos comuns
class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100, example="Carlos Silva")
    email: EmailStr = Field(..., example="carlos.motorista@email.com")
    tipo: TipoUsuario = Field(..., example=TipoUsuario.CLIENTE)


# Schema para criação de usuário (recebe a senha no corpo da requisição)
class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6, max_length=50, example="senhaSegura123")
    veiculo: Optional[VeiculoAninhadoCreate] = None  # Dados do veículo, caso seja um motorista


# Schema de resposta pública do usuário (oculta a senha criptografada por segurança)
class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    criado_em: datetime

    class Config:
        from_attributes = True  # Permite conversão direta do SQLAlchemy ORM para Pydantic

class UsuarioResumoResponse(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True  # Permite conversão direta do SQLAlchemy ORM para Pydantic

# ==========================================
# 3. SCHEMAS DE SOLICITAÇÃO DE COMANDO
# ==========================================

# Requisição que o Motorista faz pelo app/painel
class SolicitacaoComandoCreate(BaseModel):
    veiculo_id: Optional[int] = Field(None, example=1)
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
    tipo_comando: TipoComando
    status: StatusComando
    solicitado_em: datetime

    # Objetos aninhados para exibir informações do motorista e do veículo
    motorista: UsuarioResumoResponse
    veiculo: VeiculoResumoResponse

    class Config:
        from_attributes = True


# ==========================================
# 4. SCHEMAS DE AUTENTICAÇÃO E TOKEN (JWT)
# ==========================================

# 1. Requisição de Login (mantido)
class LoginSchema(BaseModel):
    login: str = Field(..., example="carlos@transp.com ou carlos")
    senha: str = Field(..., example="senhaSegura123")


# 2. Resposta Padrão do Token (mantido)
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 3. Payload Interno do Token (mantido)
class TokenData(BaseModel):
    usuario_id: Optional[int] = None
    tipo: Optional[TipoUsuario] = None


# 4. NOVO: Resposta Completa do Login para o Frontend
# (Retorna o token junto com as informações que o frontend precisa salvar no localStorage)
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nome: str
    email: EmailStr
    tipo: TipoUsuario

    class Config:
        from_attributes = True

    
