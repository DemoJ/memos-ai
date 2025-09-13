from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field

class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    memos_db_path: str = "./memos_prod.db"
    vector_db_path: str = "./vector_db"
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "gpt-3.5-turbo"
    max_search_results: int = 5
    sync_interval_hours: int = 1
    proxy: Optional[str] = None
    retrieval_score_threshold: float = Field(0.7, description="Threshold for filtering search results based on score")
    
    class Config:
        env_file = ".env"

settings = Settings()