import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote
from playwright.async_api import async_playwright

class IndeedPlaywrightScraper:
    """Scraper Ultra-Fast para mx.indeed.com con extracción HTML instantánea y bloqueo de assets."""

    def __init__(self):
        self.base_url = "https://mx.indeed.com"

    async def fetch_jobs(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        if not keywords:
            keywords = ["Full Stack", "Backend", "Frontend", "Desarrollador"]

        jobs = []
        search_terms = keywords[:4]
        locations = ["Remoto", "Mexico"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            # Bloquear recursos pesados (Imágenes, Fuentes, CSS, Anuncios)
            await context.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2,ttf,css,ico,webp}", lambda route: route.abort())
            page = await context.new_page()

            for kw in search_terms:
                for loc in locations:
                    found_in_combo = 0
                    encoded_kw = quote(kw)
                    encoded_loc = quote(loc)
                    search_url = f"{self.base_url}/ofertas?q={encoded_kw}&l={encoded_loc}&fromage=2"

                    try:
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=12000)
                        await asyncio.sleep(0.3)

                        job_cards = await page.query_selector_all("div.job_seen_beacon, td.resultContent, div.cardOutline")

                        for card in job_cards[:15]:
                            try:
                                link_el = await card.query_selector("a.jcs-JobTitle, h2.jobTitle a, a[data-jk]")
                                company_el = await card.query_selector("span[data-testid='company-name'], span.companyName, span.css-1h7lukg")
                                location_el = await card.query_selector("div[data-testid='text-location'], div.companyLocation, div.css-1restlb")
                                salary_el = await card.query_selector("div.salary-snippet-container, div.metadata.salary-snippet-container, span.css-19j1a75")
                                snippet_el = await card.query_selector("div.job-snippet, table.jobCardShelfContainer, td.snippetContainer")

                                if not link_el:
                                    continue

                                title = (await link_el.inner_text()).strip()
                                company = (await company_el.inner_text()).strip() if company_el else "Empresa Indeed"
                                location_val = (await location_el.inner_text()).strip() if location_el else loc
                                salary_text = (await salary_el.inner_text()).strip() if salary_el else ""
                                snippet_text = (await snippet_el.inner_text()).strip() if snippet_el else ""

                                href = await link_el.get_attribute("href") or ""
                                if not title or not href:
                                    continue

                                full_url = f"{self.base_url}{href}" if href.startswith("/") else href

                                jk_match = ""
                                if "jk=" in href:
                                    jk_match = href.split("jk=")[1].split("&")[0]
                                elif await link_el.get_attribute("data-jk"):
                                    jk_match = await link_el.get_attribute("data-jk")
                                job_key = f"indeed_{jk_match}" if jk_match else f"indeed_{abs(hash(href))}"

                                description_text = snippet_text if len(snippet_text) > 40 else f"Vacante de {title} en {company}. Ubicación: {location_val}. Aplicar en Indeed."

                                job_item = {
                                    "id": job_key,
                                    "title": title.strip(),
                                    "company": company.strip(),
                                    "location": location_val.strip(),
                                    "description": description_text,
                                    "salary": salary_text,
                                    "modality": "remote" if loc == "Remoto" or "remoto" in location_val.lower() else "",
                                    "url": full_url,
                                    "posted_at": datetime.now(),
                                    "source": "Indeed"
                                }

                                jobs.append(job_item)
                                found_in_combo += 1

                            except Exception:
                                continue

                        print(f"  [Indeed] '{kw}' ({loc}) -> {found_in_combo} vacantes")

                    except Exception as e:
                        print(f"  [Indeed] Error en '{kw}' ({loc}): {e}")

            await browser.close()

        unique_jobs = {j["id"]: j for j in jobs}
        return list(unique_jobs.values())
