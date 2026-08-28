import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from playwright.async_api import async_playwright

class LinkedInPlaywrightScraper:
    """Scraper Ultra-Fast para LinkedIn Jobs con soporte para filtros de país y remoto."""

    def __init__(self):
        self.base_url = "https://www.linkedin.com"

    async def fetch_jobs(
        self,
        keywords: List[str] = None,
        max_hours: float = 72.0,
        user_location: str = "Baja California, México"
    ) -> List[Dict[str, Any]]:
        if not keywords:
            keywords = ["Full Stack", "Backend", "Frontend", "Software Engineer"]

        # Calcular segundos exactos para el parámetro f_TPR de LinkedIn
        tpr_seconds = int(max_hours * 3600)
        tpr_param = f"&f_TPR=r{tpr_seconds}"

        # Extraer primer término de ubicación local limpia
        primary_local = user_location.split(",")[0].strip() if user_location else "Baja California"

        jobs = []
        search_terms = keywords[:5]
        search_configs = [
            ("Nacional (Presencial y General)", "Mexico", ""),
            ("100% Remoto", "Mexico", "&f_WT=2"),
            (f"Local ({primary_local})", primary_local, "")
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            # Bloquear imagenes y estilos pesados / Block heavy assets
            await context.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2,ttf,css,ico,webp}", lambda route: route.abort())
            page = await context.new_page()

            for term in search_terms:
                for label, loc, extra_param in search_configs:
                    url = f"https://www.linkedin.com/jobs/search?keywords={term.replace(' ', '%20')}&location={loc.replace(' ', '%20')}{tpr_param}{extra_param}"
                    found_in_combo = 0

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                        await asyncio.sleep(0.5)

                        for _ in range(2):
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(0.2)

                        job_cards = await page.query_selector_all("div.base-card, div.base-search-card, li")

                        for card in job_cards[:15]:
                            try:
                                title_elem = await card.query_selector("h3.base-search-card__title, .base-search-card__title, h3")
                                company_elem = await card.query_selector("h4.base-search-card__subtitle, .base-search-card__subtitle, h4")
                                link_elem = await card.query_selector("a.base-card__full-link, a.base-search-card__full-link, a[href*='/jobs/view/']")
                                location_elem = await card.query_selector("span.job-search-card__location, .base-search-card__metadata span")
                                time_elem = await card.query_selector("time")

                                if not title_elem or not link_elem:
                                    continue

                                title = (await title_elem.inner_text()).strip()
                                company = (await company_elem.inner_text()).strip() if company_elem else "Empresa LinkedIn"
                                raw_job_url = await link_elem.get_attribute("href") or ""
                                clean_job_url = raw_job_url.split("?")[0]
                                location = (await location_elem.inner_text()).strip() if location_elem else "México"
                                time_text = (await time_elem.inner_text()).strip() if time_elem else ""

                                if not title or not clean_job_url or "/jobs/" not in clean_job_url:
                                    continue

                                # Descartar subdominios foraneos locales / Discard foreign subdomains
                                if any(prefix in clean_job_url.lower() for prefix in ["cl.linkedin", "ar.linkedin", "pe.linkedin", "uy.linkedin", "ve.linkedin", "ec.linkedin", "es.linkedin"]):
                                    continue

                                job_id = ""
                                id_match = re.search(r'/jobs/view/(\d+)', raw_job_url)
                                if not id_match:
                                    id_match = re.search(r'-(\d{7,})\?', raw_job_url)
                                if not id_match:
                                    id_match = re.search(r'currentJobId=(\d+)', raw_job_url)

                                if id_match:
                                    job_id = id_match.group(1)
                                else:
                                    job_id = str(abs(hash(clean_job_url)))

                                job_key = f"linkedin_{job_id}"
                                is_explicit_remote = "f_WT=2" in extra_param or "remoto" in location.lower() or "remote" in location.lower()
                                is_english_title = any(w in title.lower() for w in ["engineer", "developer", "lead", "architect", "manager", "analyst", "remote work", "full stack", "fullstack", "backend", "frontend"]) and not any(w in title.lower() for w in ["desarrollador", "ingeniero", "programador", "practicante"])

                                if is_english_title:
                                    desc = f"Job opportunity for {title} at {company} ({location}). {f'Posted {time_text}.' if time_text else ''} Direct application via LinkedIn."
                                else:
                                    desc = f"Oportunidad laboral de {title} en {company} ({location}). {f'Publicada hace {time_text}.' if time_text else ''} Postulación directa vía LinkedIn."

                                job_obj = {
                                    "id": job_key,
                                    "title": title,
                                    "company": company,
                                    "url": clean_job_url,
                                    "location": location if location else "México",
                                    "description": desc,
                                    "salary": "",
                                    "modality": "remote" if is_explicit_remote else "",
                                    "posted_at": datetime.now() - timedelta(hours=min(max_hours, 24.0)),
                                    "source": "LinkedIn"
                                }

                                jobs.append(job_obj)
                                found_in_combo += 1

                            except Exception:
                                continue

                        print(f"  [LinkedIn] '{term}' ({label}) -> {found_in_combo} vacantes")

                    except Exception as e:
                        print(f"  [LinkedIn] Error en '{term}' ({label}): {e}")

            await browser.close()

        unique_jobs = {j["id"]: j for j in jobs}
        return list(unique_jobs.values())
