"""Configuración de la aplicación mediante variables de entorno."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración cargada desde .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Sistema Predictivo API"
    debug: bool = False

    # Machine Learning
    ml_model_dir: str = "ml_models"

    # Supabase Storage (artefactos ML — requerido en producción)
    supabase_project_url: str = "https://xitzatipxgwbfxlpsllg.supabase.co"
    supabase_service_role_key: str = "sb_publishable_UFtziML9MyVSKFkOggkmUA_YcTFxbVo"  # service_role key (para subir archivos)
    supabase_storage_bucket: str = "modelos_prediccion"
    gdrive_iter_imputer_id: str = "1stoh8-KlX1mKw0tLtdoxC6j9TyO6AKoN"     # ID del archivo iter_imputer.pkl en Google Drive

    # JWT
    jwt_secret_key: str = "cambiar-en-produccion-clave-secreta-muy-segura"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 horas

    # PostgreSQL 17
    # postgres_host: str = "127.0.0.1"
    # postgres_port: int = 5432
    # postgres_user: str = "postgres"
    # postgres_password: str = ""
    # postgres_db: str = "sistema_predictivo_bd"

    postgres_host: str = "aws-1-us-east-1.pooler.supabase.com"
    postgres_port: int = 5432
    postgres_user: str = "postgres.xitzatipxgwbfxlpsllg"
    postgres_password: str = "helen2026.sistemapredictivo"
    postgres_db: str = "postgres"

    @property
    def database_url_async(self) -> str:
        """URL para SQLAlchemy con driver asyncpg (uso en la app)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """URL para Alembic y scripts síncronos (psycopg2)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
