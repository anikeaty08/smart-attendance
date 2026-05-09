from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:aniket@localhost:5432/attendance"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12
    allowed_domains: str = "bmsit.in"
    google_client_id: str | None = None
    default_radius_meters: int = 10
    max_radius_meters: int = 30
    max_gps_accuracy_meters: int = 50
    default_session_minutes: int = 5
    admin_default_password: str = "admin123"
    correction_window_hours: int = 48

    @property
    def domains(self) -> set[str]:
        return {d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()}


settings = Settings()
