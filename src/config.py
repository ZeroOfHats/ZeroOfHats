from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@postgres/appdb"
    # Add other settings as needed

    class Config:
        # Construct path to project root .env file
        # os.path.abspath(__file__) gives the absolute path of config.py
        # os.path.dirname() is called twice to go up two levels (from src/ to project root)
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        env_file = env_file_path
        extra = "ignore"

settings = Settings()
