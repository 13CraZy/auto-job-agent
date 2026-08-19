from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseScraper(ABC):
    """Clase base abstracta para scrapers de vacantes de empleo."""

    @abstractmethod
    async def fetch_jobs(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Busca y extrae vacantes según una lista de palabras clave.
        Debe devolver una lista de diccionarios con la estructura:
        {
            "id": str,
            "title": str,
            "company": str,
            "url": str,
            "location": str,
            "description": str,
            "posted_at": datetime,
            "source": str
        }
        """
        pass
