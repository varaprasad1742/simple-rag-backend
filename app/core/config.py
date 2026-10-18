from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FRONTEND_URL: str = "http://localhost:5173"
    APP_NAME: str = "RAG Platform"

    SECRET_KEY: str = "36cbc51bf6c02173359efbaace36fc341efb771a98fee38270fe8efd34d14366"
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/rag.db"

    # Embedded local disk folder storage by default (no Qdrant server needed)
    QDRANT_URL: str = "./data/qdrant"
    QDRANT_API_KEY: str = ""
    
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()