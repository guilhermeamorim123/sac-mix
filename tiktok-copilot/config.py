"""Configuracao central, lida do .env uma unica vez."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "sim")


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    model: str
    tiktok_username: str

    auto_reply_enabled: bool
    auto_reply_max_per_min: int
    chrome_cdp_url: str

    # Replay = live gravada sendo reexibida. Nesse modo o auto-envio so libera
    # com check-in de supervisor, porque nao ha ninguem na frente da camera.
    replay_mode: bool
    supervisor_interval_min: int

    store_backend: str
    sqlite_path: str
    supabase_url: str
    supabase_service_key: str
    seller_id: str

    # Janela de agrupamento: mensagens que chegam dentro desse intervalo sao
    # classificadas em uma unica chamada. Chat de live vem em rajada, entao
    # isso corta custo e latencia de forma significativa.
    batch_window_seconds: float = 1.5
    batch_max_size: int = 12

    # Acima disso o lead entra na aba "quentes" do painel.
    hot_lead_threshold: int = 7

    @classmethod
    def load(cls) -> "Config":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY nao definida. Copie .env.example para .env.")

        username = os.getenv("TIKTOK_USERNAME", "").strip()
        if not username:
            raise RuntimeError("TIKTOK_USERNAME nao definida.")
        if not username.startswith("@"):
            username = "@" + username

        backend = os.getenv("STORE_BACKEND", "sqlite").strip().lower()
        if backend not in ("sqlite", "supabase"):
            raise RuntimeError(f"STORE_BACKEND invalido: {backend!r}. Use 'sqlite' ou 'supabase'.")

        return cls(
            anthropic_api_key=key,
            model=os.getenv("COPILOT_MODEL", "claude-opus-5"),
            tiktok_username=username,
            auto_reply_enabled=_bool("AUTO_REPLY_ENABLED"),
            auto_reply_max_per_min=int(os.getenv("AUTO_REPLY_MAX_PER_MIN", "4")),
            chrome_cdp_url=os.getenv("CHROME_CDP_URL", "http://localhost:9222"),
            replay_mode=_bool("REPLAY_MODE"),
            supervisor_interval_min=int(os.getenv("SUPERVISOR_INTERVAL_MIN", "15")),
            store_backend=backend,
            sqlite_path=os.getenv("SQLITE_PATH", "copilot.db"),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
            seller_id=os.getenv("SELLER_ID", "default"),
        )
