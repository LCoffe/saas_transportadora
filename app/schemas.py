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

class VeiculoResumoResponse(VeiculoBase):
    id: int
    placa: str
    modelo: str

    class Config:
        from_attributes = True

class VeiculoUpdate(BaseModel):
    placa: Optional[str] = Field(None, min_length=7, max_length=10)
    modelo: Optional[str] = Field(None, max_length=50)
    marca: Optional[str] = Field(None, max_length=50)
    ano: Optional[int] = None

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

# Schema para atualização de usuário (todos os campos opcionais)
class UsuarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    tipo: Optional[TipoUsuario] = None
    senha: Optional[str] = Field(None, min_length=6, max_length=50)
    ativo: Optional[bool] = None
    veiculo: Optional[VeiculoUpdate] = None  # Permite atualizar os dados do veículo, caso seja um motorista

# Schema de resposta pública do usuário (oculta a senha criptografada por segurança)
class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    criado_em: datetime
    veiculo: Optional[VeiculoResumoResponse] = None  # Inclui os dados do veículo, caso seja um motorista

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

  
class HistoricoDecisaoResponse(BaseModel):
    id: int
    comando_id: int
    operador_id: int
    decisao: str
    observacao: Optional[str] = None
    data_decisao: datetime

    class Config:
        from_attributes = True

# Schemas auxiliares para evitar erros de validação com relacionamentos
class MotoristaSimplesResponse(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True # Ou orm_mode = True se estiver no Pydantic v1

class VeiculoSimplesResponse(BaseModel):
    id: int
    placa: str
    modelo: Optional[str] = None

    class Config:
        from_attributes = True

# Schema de resposta simples para o operador/funcionário
class FuncionarioSimplesResponse(BaseModel):
    id: int
    nome: Optional[str] = None
    email: str

    class Config:
        from_attributes = True

# Atualização no schema principal
class SolicitacaoComandoResponse(BaseModel):
    id: int
    veiculo_id: int
    motorista_id: int
    tipo_comando: str
    status: str
    solicitado_em: datetime
    
    observacao: Optional[str] = None
    funcionario_id: Optional[int] = None
    respondido_em: Optional[datetime] = None

    motorista: Optional[MotoristaSimplesResponse] = None
    veiculo: Optional[VeiculoSimplesResponse] = None
    funcionario: Optional[FuncionarioSimplesResponse] = None  # <--- NOVO CAMPO RETORNADO

    class Config:
        from_attributes = True

class CriarEncomendaSchema(BaseModel):
    descricao: str
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str

class EncomendaResponse(BaseModel):
    id: int
    serial: str
    descricao: str
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str
    criado_em: datetime

    class Config:
        from_attributes = True

class EncomendaResumoSchema(BaseModel):
    id: int
    descricao: str

    class Config:
        from_attributes = True

class RotaDisponivelResponse(BaseModel):
    id: int
    serial: str
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str
    status: str
    criado_em: datetime
    encomenda: Optional[EncomendaResumoSchema] = None

    class Config:
        from_attributes = True

class AceitarRotaSchema(BaseModel):
    motorista_id: int

class RotaIniciadaResponse(BaseModel):
    id: int
    serial: str
    rota_id: int
    encomenda_id: int
    motorista_id: int
    status: str
    iniciada_em: datetime

    class Config:
        from_attributes = True