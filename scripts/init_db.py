from app.database import engine, Base
from app.models import Licitacion

Base.metadata.create_all(bind=engine)
print("Tablas creadas correctamente")
