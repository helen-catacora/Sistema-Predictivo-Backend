# Sistema Predictivo - Backend

API REST desarrollada con **FastAPI** y **PostgreSQL 17**.

## Requisitos

- Python 3.11+
- PostgreSQL 17
- Entorno virtual recomendado (venv o similar)

## Estructura del proyecto

```
sistemapredictivoBackend/
├── app/
│   ├── api/              # Routers y endpoints
│   │   └── endpoints/
│   ├── core/             # Configuración, DB, utilidades
│   ├── models/           # Modelos SQLAlchemy
│   ├── schemas/          # Esquemas Pydantic
│   ├── services/         # Lógica de negocio
│   ├── repositories/     # Acceso a datos (opcional)
│   └── main.py           # Entrada de la aplicación
├── .env.example
├── requirements.txt
└── README.md
```

## Instalación

1. Clonar o abrir el proyecto y crear entorno virtual:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Linux/macOS
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Configurar variables de entorno:

   - Copiar `.env.example` a `.env`
   - Ajustar `POSTGRES_*` con los datos de tu PostgreSQL 17

4. Crear la base de datos en PostgreSQL (si no existe):

   ```sql
   CREATE DATABASE sistemapredictivo;
   ```

## Ejecución

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Documentación Swagger: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

## Próximos pasos

- Añadir modelos en `app/models/` y registrarlos en `app/core/database.py` (Base).
- Definir esquemas en `app/schemas/` para validación y serialización.
- Crear endpoints en `app/api/endpoints/` y registrarlos en `app/api/__init__.py`.
- Opcional: configurar Alembic para migraciones (`alembic init` ya está en dependencias).
