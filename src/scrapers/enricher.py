import asyncio
import json
import re
import html as html_lib
from typing import List, Dict, Any, Optional
import httpx

class JobDetailEnricher:
    """
    Recupera la descripción completa y detalles enriquecidos de las vacantes accediendo
    a las URLs reales de cada portal de manera asíncrona y ultrarrápida.
    """

    def __init__(self, concurrency: int = 8, timeout: float = 10.0):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }

    async def enrich_job(self, job: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        url = job.get("url", "")
        source = job.get("source", "").lower()
        if not url or url == "#":
            return job

        # Si ya tiene una descripción suficientemente larga (p. ej. RemoteOK que trae el texto completo)
        current_desc = job.get("description", "")
        if len(current_desc) > 800 and not current_desc.startswith("Vacante de") and not current_desc.startswith("Job opportunity for"):
            return job

        async with self.semaphore:
            try:
                resp = await client.get(url, timeout=self.timeout, follow_redirects=True)
                if resp.status_code != 200:
                    return job
                
                html_text = resp.text
                full_desc = self._extract_description_from_html(html_text, source)
                
                if full_desc and len(full_desc) > len(current_desc):
                    job["description"] = full_desc

                # Extracción adicional de modalidad o salario si el detalle lo tiene
                extracted_salary = self._extract_salary_from_html(html_text)
                if extracted_salary and not job.get("salary"):
                    job["salary"] = extracted_salary

            except Exception:
                pass

        return job

    def _extract_description_from_html(self, html_text: str, source: str) -> str:
        # 1. Intentar JSON-LD estructurado Schema.org JobPosting
        json_ld_matches = re.findall(r'<script\s+type=[\'"]application/ld\+json[\'"]>([\s\S]*?)</script>', html_text, re.IGNORECASE)
        for m in json_ld_matches:
            try:
                data = json.loads(m.strip())
                items = data if isinstance(data, list) else data.get("@graph", [data])
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        raw_d = item.get("description", "")
                        if raw_d:
                            clean = re.sub(r'<[^>]+>', ' ', raw_d)
                            clean = html_lib.unescape(clean)
                            cleaned_str = " ".join(clean.split())
                            if len(cleaned_str) > 60:
                                return cleaned_str
            except Exception:
                continue

        # 2. LinkedIn Markup
        li_match = re.search(r'class="show-more-less-html__markup[^"]*">([\s\S]*?)</div>', html_text)
        if li_match:
            clean = re.sub(r'<[^>]+>', ' ', li_match.group(1))
            clean_str = " ".join(html_lib.unescape(clean).split())
            if len(clean_str) > 60:
                return clean_str

        # 3. Indeed Job Description
        ind_match = re.search(r'id="jobDescriptionText"[^>]*>([\s\S]*?)</div>', html_text)
        if ind_match:
            clean = re.sub(r'<[^>]+>', ' ', ind_match.group(1))
            clean_str = " ".join(html_lib.unescape(clean).split())
            if len(clean_str) > 60:
                return clean_str

        # 4. Computrabajo Paragraphs (p.mbB o fs16)
        ct_p_matches = re.findall(r'<p[^>]*class="[^"]*(?:mbB|fs16)[^"]*"[^>]*>([\s\S]*?)</p>', html_text, re.IGNORECASE)
        for p_html in ct_p_matches:
            clean = re.sub(r'<[^>]+>', ' ', p_html)
            clean_str = " ".join(html_lib.unescape(clean).split())
            if len(clean_str) > 120 and not clean_str.startswith("Palabras clave:") and not clean_str.startswith("Competencias"):
                return clean_str

        # 5. Computrabajo Containers (box_detail, box_border, section)
        ct_match = re.search(r'<(?:div|section)[^>]*class="[^"]*(?:box_detail|box_border|fs16|detail_offer)[^"]*"[^>]*>([\s\S]*?)</(?:div|section)>', html_text, re.IGNORECASE)
        if ct_match:
            clean = re.sub(r'<[^>]+>', ' ', ct_match.group(1))
            clean_str = " ".join(html_lib.unescape(clean).split())
            if len(clean_str) > 80:
                return clean_str

        # 6. Generic meta description fallback
        meta_match = re.search(r'<meta\s+name=[\'"]description[\'"]\s+content=[\'"]([\s\S]*?)[\'"]', html_text, re.IGNORECASE)
        if meta_match:
            clean_str = html_lib.unescape(meta_match.group(1)).strip()
            if len(clean_str) > 80:
                return clean_str

        return ""

    def _extract_salary_from_html(self, html_text: str) -> str:
        sal_match = re.search(r'\$\s*[\d,\.]+\s*(?:a\s*\$\s*[\d,\.]+|\s*al\s*mes|\s*mensual|\s*mensuales|\s*netos|\s*brutos)?', html_text, re.IGNORECASE)
        if sal_match:
            return sal_match.group(0).strip()
        return ""

    async def enrich_all(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
            tasks = [self.enrich_job(job, client) for job in jobs]
            return await asyncio.gather(*tasks)
