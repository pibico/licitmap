from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base

class Licitacion(Base):
    __tablename__ = "licitaciones"

    id = Column(Integer, primary_key=True, index=True)
    expediente = Column(String, unique=True, index=True)
    titulo = Column(String)
    organo_contratacion = Column(String)
    estado = Column(String)
    presupuesto = Column(Float)
    fecha_publicacion = Column(DateTime)
    comunidad_autonoma = Column(String)
    url = Column(String)
