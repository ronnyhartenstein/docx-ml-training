from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Modell-Pfade
    base_model_path: str = "./models/llama3.1-8b-base"
    finetuned_model_path: str = "./models/ppsneo-finetuned"
    adapter_path: str = "./models/adapters"

    # Server-Ports
    mlx_server_host: str = "localhost"
    mlx_server_port: int = 8080
    api_port: int = 8000

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    qa_generator_model: str = "llama3.1:8b"

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Trainingsdaten
    qa_per_chunk: int = 3
    train_split: float = 0.8

    # Pfade (abgeleitet)
    @property
    def raw_docs_dir(self) -> Path:
        return Path("data/raw")

    @property
    def extracted_dir(self) -> Path:
        return Path("data/extracted")

    @property
    def training_dir(self) -> Path:
        return Path("data/training")

    @property
    def mlx_server_url(self) -> str:
        return f"http://{self.mlx_server_host}:{self.mlx_server_port}"


settings = Settings()
