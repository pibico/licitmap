from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from app.database import Base

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
