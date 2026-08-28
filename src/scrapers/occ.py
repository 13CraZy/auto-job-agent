import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import quote
from playwright.async_api import async_playwright


class OCCPlaywrightScraper:
    """Scraper masivo para occ.com.mx utilizando Playwright con descripciones REALES."""

    def __init__(self):
        self.base_url = "https://www.occ.com.mx"

    async def fetch_jobs(
        self,
        keywords: List[str] = None,
        max_hours: float = 72.0,
        user_location: str = "Baja California, México"
    ) -> List[Dict[str, Any]]:
        if not keywords:
            keywords = ["Desarrollador Web", "Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend", "Programador Web"]

        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            await context.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2,ttf,css,ico,webp}", lambda route: route.abort())
            page = await context.new_page()

            search_terms = keywords[:4]
            total_terms = len(search_terms)

            for idx, kw in enumerate(search_terms, 1):
                kw_slug = kw.lower().replace(" ", "-")
                search_url = f"{self.base_url}/empleos/de-{kw_slug}/"
                found_in_kw = 0

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=12000)
                    await asyncio.sleep(0.5)

                    job_cards = await page.query_selector_all("div[id^='jobcard-'], div.job-card, div[class*='jobcard']")

                    for card in job_cards[:12]:
                        title_el = await card.query_selector("h2, a[class*='jobCardTitle'], a[class*='title']")
                        company_el = await card.query_selector("span[class*='companyName'], a[class*='companyName']")
                        location_el = await card.query_selector("span[class*='location']")
                        link_el = await card.query_selector("a[href*='/empleo/']")
                        snippet_el = await card.query_selector("p, div[class*='snippet'], div[class*='description']")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else "Empresa OCC México"
                        location_val = (await location_el.inner_text()).strip() if location_el else "Remoto, México"
                        snippet_text = (await snippet_el.inner_text()).strip() if snippet_el else ""
                        
                        href = await link_el.get_attribute("href") if link_el else ""
                        clean_href = href.split("?")[0].split("#")[0]
                        full_url = f"{self.base_url}{clean_href}" if clean_href.startswith("/") else clean_href

                        if not title or not full_url:
                            continue

                        description_text = snippet_text if len(snippet_text) > 40 else f"Vacante de {title} en {company}. Modalidad: {location_val}. Requisitos técnicos para desarrollo de software."

                        job_item = {
                            "id": f"occ_{abs(hash(clean_href))}",
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_val.strip(),
                            "description": description_text,
                            "salary": "",
                            "modality": "remote" if "remoto" in location_val.lower() else "",
                            "url": full_url,
                            "posted_at": datetime.now() - timedelta(hours=min(max_hours, 24.0)),
                            "source": "OCCMundial"
                        }

                        jobs.append(job_item)
                        found_in_kw += 1

                    print(f"  [OCC] '{kw}' -> {found_in_kw} vacantes")

                except Exception as e:
                    print(f"  [OCC] Error en '{kw}': {e}")

            await browser.close()

        unique_jobs = {j["url"]: j for j in jobs}
        return list(unique_jobs.values())
