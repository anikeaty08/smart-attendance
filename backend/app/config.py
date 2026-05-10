from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:aniket@localhost/attendance"
    allowed_domains: str = "bmsit.in,student.bmsit.in"
    clerk_secret_key: str = ""
    next_public_clerk_publishable_key: str = ""
    default_radius_meters: int = 10
    max_radius_meters: int = 30
    max_gps_accuracy_meters: int = 50
    default_session_minutes: int = 5
    correction_window_hours: int = 48

    @property
    def domains(self) -> set[str]:
        return {d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()}

    @property
    def clerk_jwks_url(self) -> str:
        # Derive JWKS URL from publishable key
        # pk_test_<base64-encoded-frontend-api-url>
        # The JWKS endpoint is at: https://<frontend-api>/.well-known/jwks.json
        import base64
        key_body = self.next_public_clerk_publishable_key.split("_", 2)[-1]
        # Pad base64 if needed
        pad = 4 - len(key_body) % 4
        if pad != 4:
            key_body += "=" * pad
        try:
            frontend_api = base64.b64decode(key_body.encode()).decode().rstrip("$")
            return f"https://{frontend_api}/.well-known/jwks.json"
        except Exception:
            return ""


settings = Settings()
