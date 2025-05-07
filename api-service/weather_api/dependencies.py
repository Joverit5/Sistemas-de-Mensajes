"""
Dependency injection for the Weather API service
"""
from weather_api.repositories.postgres_repository import PostgresRepository

# Singleton repository instance
_repository = None


def get_repository() -> PostgresRepository:
    """Get or create the repository instance"""
    global _repository
    if _repository is None:
        _repository = PostgresRepository()
    return _repository
