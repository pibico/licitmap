from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean
from app.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)   # solo admin
    email = Column(String, nullable=True)              # usuarios no-admin
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    language = Column(String(2), default="es", nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class Licitacion(Base):
    __tablename__ = "licitaciones"

    id = Column(Integer, primary_key=True, index=True)
    atom_id = Column(String, unique=True, index=True)
    expediente = Column(String, index=True)
    titulo = Column(String)
    organo_contratacion = Column(String)
    estado = Column(String)
    presupuesto = Column(Float)
    fecha_publicacion = Column(DateTime)
    fecha_limite = Column(Date)
    tipo_contrato = Column(String)
    comunidad_autonoma = Column(String)
    pais = Column(String)
    url = Column(String)
    cpv = Column(String)
    municipio = Column(String, index=True)
    codigo_postal = Column(String, index=True)
    provincia = Column(String, index=True)


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)        # newsletter | alerta | suscripcion
    keywords = Column(String, nullable=True)
    cpv_codes = Column(String, nullable=True)    # pipe-separated
    tipo_contrato = Column(String, nullable=True)
    comunidades = Column(String, nullable=True)  # pipe-separated
    provincias = Column(String, nullable=True)
    presupuesto_min = Column(Float, nullable=True)
    presupuesto_max = Column(Float, nullable=True)
    solo_activas = Column(Boolean, default=False)
    entidad_tipo = Column(String, nullable=True)  # ccaa|provincia|organismo|cpv
    entidad_valor = Column(String, nullable=True)
    frecuencia = Column(String, default="diaria")  # diaria|semanal
    dia_semana = Column(Integer, default=0)          # 0=lun..6=dom
    hora_envio = Column(Integer, default=8)
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_checked_at = Column(DateTime, nullable=True)


class LicitacionSeguida(Base):
    __tablename__ = "licitaciones_seguidas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    licitacion_id = Column(Integer, nullable=False, index=True)
    notif_cambio_estado = Column(Boolean, default=True, nullable=False)
    notif_dias_vencimiento = Column(Integer, nullable=True)  # NULL|3|7|15
    last_estado = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
