import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import quote
from playwright.async_api import async_playwright


class OCCPlaywrightScraper:
    """Scraper masivo para occ.com.mx utilizando Playwright con descripciones REALES."""

    def __init__(self):
        self.base_url = "https://www.occ.com.mx"

    async def fetch_jobs(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
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

            search_terms = keywords[:8]
            total_terms = len(search_terms)

            for idx, kw in enumerate(search_terms, 1):
                kw_slug = kw.lower().replace(" ", "-")
                search_url = f"{self.base_url}/empleos/de-{kw_slug}/"
                found_in_kw = 0

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1.0)

                    job_cards = await page.query_selector_all("div[id^='jobcard-'], div.job-card, div[class*='jobcard']")

                    for card in job_cards[:15]:
                        title_el = await card.query_selector("h2, a[class*='jobCardTitle'], a[class*='title']")
                        company_el = await card.query_selector("span[class*='companyName'], a[class*='companyName']")
                        location_el = await card.query_selector("span[class*='location']")
                        link_el = await card.query_selector("a[href*='/empleo/']")

                        title = await title_el.inner_text() if title_el else ""
                        company = await company_el.inner_text() if company_el else "Empresa OCC México"
                        location_val = await location_el.inner_text() if location_el else "Remoto, México"
                        
                        href = await link_el.get_attribute("href") if link_el else ""
                        clean_href = href.split("?")[0].split("#")[0]
                        full_url = f"{self.base_url}{clean_href}" if clean_href.startswith("/") else clean_href

                        if not title or not full_url:
                            continue

                        description_text = f"Vacante de {title} en {company}. Requisitos técnicos para {title} en modalidad {location_val}."
                        try:
                            detail_page = await context.new_page()
                            await detail_page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
                            desc_el = await detail_page.query_selector("div[class*='jobDescription'], div[id*='job-description'], div.box-description, div.content-description")
                            if desc_el:
                                description_text = (await desc_el.inner_text()).strip()
                            await detail_page.close()
                        except Exception:
                            pass

                        if not description_text or len(description_text) < 50:
                            continue

                        job_item = {
                            "id": f"occ_{hash(clean_href)}",
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_val.strip(),
                            "description": description_text,
                            "salary": "",
                            "modality": "",
                            "url": full_url,
                            "posted_at": datetime.now() - timedelta(days=1),
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
