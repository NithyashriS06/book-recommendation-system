from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "goodreads_rl"
    DB_USER: str = "rl_user"
    DB_PASSWORD: str = "rl_password"

    MODEL_PATH: str = "models/dqn_model.pt"
    EPISODE_LENGTH: int = 10
    TOP_K: int = 10
    CANDIDATE_POOL_SIZE: int = 500

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
