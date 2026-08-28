from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Directorio base del proyecto / Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    Configuracion global del sistema cargada desde variables de entorno (.env).
    Global system configuration loaded from environment variables (.env).
    """

    # ============================================================
    # PROVEEDORES DE INTELIGENCIA ARTIFICIAL / AI PROVIDERS
    # ============================================================
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    
    # ============================================================
    # CANAL DE TELEGRAM BOT / TELEGRAM BOT CHANNEL
    # ============================================================
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    ENABLE_TELEGRAM: bool = True
    
    # ============================================================
    # CANAL DE CORREO ELECTRONICO (SMTP) / EMAIL SMTP CHANNEL
    # ============================================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""
    ENABLE_EMAIL: bool = False
    
    # ============================================================
    # FILTROS Y VENTANAS DE TIEMPO / FILTERS & TIME WINDOWS
    # ============================================================
    MAX_HOURS_OLD: float = 72.0
    DEFAULT_COUNTRY: str = "Mexico"
    
    # ============================================================
    # RUTAS DEL SISTEMA / SYSTEM FILE PATHS
    # ============================================================
    BASE_DIR: Path = BASE_DIR
    OUTPUT_DIR: Path = BASE_DIR / "vacantes"
    PROFILE_PATH: Path = BASE_DIR / "config" / "user_profile.json"
    PROCESSED_JOBS_PATH: Path = BASE_DIR / "config" / "processed_jobs.json"
    USER_PREFS_PATH: Path = BASE_DIR / ".user_preferences.json"

    @property
    def profile_path_resolved(self) -> Path:
        if self.PROFILE_PATH.exists():
            return self.PROFILE_PATH
        example = self.BASE_DIR / "config" / "user_profile.example.json"
        if example.exists():
            return example
        return self.PROFILE_PATH

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
