from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseScraper(ABC):
    """Clase base abstracta para scrapers de vacantes de empleo."""

    @abstractmethod
    async def fetch_jobs(
        self,
        keywords: List[str] = None,
        max_hours: float = 72.0,
        user_location: str = "Baja California, México"
    ) -> List[Dict[str, Any]]:
        """
        Busca y extrae vacantes según una lista de palabras clave y ventana de horas.
        Debe devolver una lista de diccionarios con la estructura estándar de vacante.
        """
        pass
