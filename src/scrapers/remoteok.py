import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any
from src.scrapers.base import BaseScraper


class RemoteOKScraper(BaseScraper):
    """Scraper para la API pública de RemoteOK."""

    def __init__(self):
        self.api_url = "https://remoteok.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_jobs(self, keywords: List[str]) -> List[Dict[str, Any]]:
        jobs = []
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            try:
                response = await client.get(self.api_url)
                if response.status_code == 200:
                    raw_data = response.json()
                    if isinstance(raw_data, list) and len(raw_data) > 1:
                        for item in raw_data[1:]:
                            title = item.get("position", "")
                            tags = [t.lower() for t in item.get("tags", [])]
                            description = item.get("description", "")
                            
                            matches_keywords = any(kw.lower() in title.lower() or kw.lower() in tags for kw in keywords)
                            if not matches_keywords:
                                continue

                            date_val = item.get("date")
                            if isinstance(date_val, (int, float)):
                                posted_at = datetime.fromtimestamp(date_val, tz=timezone.utc).replace(tzinfo=None)
                            elif isinstance(date_val, str) and date_val.isdigit():
                                posted_at = datetime.fromtimestamp(int(date_val), tz=timezone.utc).replace(tzinfo=None)
                            else:
                                posted_at = datetime.now()

                            salary_min = item.get("salary_min", "")
                            salary_max = item.get("salary_max", "")
                            salary_text = f"${salary_min}-${salary_max}" if salary_min else ""

                            job_obj = {
                                "id": str(item.get("id", "")),
                                "title": title,
                                "company": item.get("company", "Empresa Confidencial"),
                                "url": item.get("url", "https://remoteok.com"),
                                "location": item.get("location", "Remote / Worldwide"),
                                "description": description,
                                "salary": salary_text,
                                "modality": "remote",
                                "posted_at": posted_at,
                                "source": "RemoteOK"
                            }

                            jobs.append(job_obj)
            except Exception as e:
                print(f"[RemoteOKScraper] Error al obtener vacantes: {e}")
        return jobs
