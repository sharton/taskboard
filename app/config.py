import os

class Settings:
    app_name: str = os.getenv("APP_NAME", "TaskBoard")
    database_url: str = os.getenv(
        "DATABASE_URL",
        
    )


settings = Settings()
