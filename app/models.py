import enum
from datetime import datetime
from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Enum, 
    DateTime, 
    ForeignKey, 
    Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


# --- Enumerações (Tipos Enumerados) ---

class TipoUsuario(str, enum.Enum):
    CLIENTE = "CLIENTE"            # Motorista do caminhão
    FUNCIONARIO = "FUNCIONARIO"    # Operador da central de monitoramento


class StatusComando(str, enum.Enum):
    PENDENTE = "PENDENTE"    # Aguardando aprovação do funcionário
    APROVADO = "APROVADO"    # Aprovado pela central, pronto para envio
    REJEITADO = "REJEITADO"  # Negado pelo funcionário
    EXECUTADO = "EXECUTADO"  # Sinal recebido e executado pelo caminhão


class TipoComando(str, enum.Enum):
    DESTRANCAR_BAU = "DESTRANCAR_BAU"
    TRANCAR_BAU = "TRANCAR_BAU"
    BLOQUEAR_IGNICAO = "BLOQUEAR_IGNICAO"
    DESBLOQUEAR_IGNICAO = "DESBLOQUEAR_IGNICAO"


# --- Mapeamento das Tabelas Relacionais (POO) ---

class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    tipo = Column(Enum(TipoUsuario), nullable=False, default=TipoUsuario.CLIENTE)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    veiculos = relationship("VeiculoModel", back_populates="proprietario")
    comandos_solicitados = relationship(
        "SolicitacaoComandoModel", 
        foreign_keys="SolicitacaoComandoModel.motorista_id",
        back_populates="motorista"
    )
    comandos_aprovados = relationship(
        "SolicitacaoComandoModel", 
        foreign_keys="SolicitacaoComandoModel.funcionario_id",
        back_populates="funcionario"
    )


class VeiculoModel(Base):
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    placa = Column(String(10), unique=True, index=True, nullable=False)
    modelo = Column(String(50), nullable=False)
    marca = Column(String(50), nullable=True)
    ano = Column(Integer, nullable=True)
    
    # Chave estrangeira que liga o veículo ao seu proprietário/motorista
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    # Relacionamentos
    proprietario = relationship("UsuarioModel", back_populates="veiculos")
    comandos = relationship("SolicitacaoComandoModel", back_populates="veiculo")


class SolicitacaoComandoModel(Base):
    __tablename__ = "comandos_solicitados"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Relacionamentos de Chave Estrangeira
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    motorista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    funcionario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # Nulo até ser aprovado/rejeitado

    # Detalhes do comando
    tipo_comando = Column(Enum(TipoComando), nullable=False)
    status = Column(Enum(StatusComando), default=StatusComando.PENDENTE, nullable=False)
    observacao = Column(String(255), nullable=True)  # Ex: "Aprovado via validação por chamada/chat"

    # Marcas de Tempo (Auditoria)
    solicitado_em = Column(DateTime, default=datetime.utcnow)
    respondido_em = Column(DateTime, nullable=True)

    # Propriedades de relacionamento ORM
    veiculo = relationship("VeiculoModel", back_populates="comandos")
    motorista = relationship("UsuarioModel", foreign_keys=[motorista_id], back_populates="comandos_solicitados")
    funcionario = relationship("UsuarioModel", foreign_keys=[funcionario_id], back_populates="comandos_aprovados")
