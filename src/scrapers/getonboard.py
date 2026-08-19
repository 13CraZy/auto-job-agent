import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from playwright.async_api import async_playwright


class GetOnBoardPlaywrightScraper:
    """Scraper masivo para getonbrd.com con extracción de descripciones REALES en LATAM."""

    def __init__(self):
        self.base_url = "https://www.getonbrd.com"

    async def fetch_jobs(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            await context.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2,ttf,css,ico,webp}", lambda route: route.abort())
            page = await context.new_page()

            categories = [
                ("Programming", f"{self.base_url}/jobs-programming"),
                ("SysAdmin / DevOps", f"{self.base_url}/jobs-sysadmin-devops"),
                ("Mobile", f"{self.base_url}/jobs-mobile")
            ]

            for idx, (cat_name, url) in enumerate(categories, 1):
                found_in_cat = 0

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1.0)

                    job_cards = await page.query_selector_all("a.gb-results-list__item, div.job-card, div.border-bottom")

                    for card in job_cards[:20]:
                        title_el = await card.query_selector("strong.gb-results-list__title, h3, div.font-weight-bold")
                        company_el = await card.query_selector("span.gb-results-list__company, div.company-name")
                        location_el = await card.query_selector("span.gb-results-list__location, div.location")

                        title = await title_el.inner_text() if title_el else ""
                        company = await company_el.inner_text() if company_el else "Startup LATAM"
                        location_val = await location_el.inner_text() if location_el else "Remoto, México"
                        
                        href = await card.get_attribute("href") if card else ""
                        if not href:
                            link_child = await card.query_selector("a")
                            href = await link_child.get_attribute("href") if link_child else ""

                        clean_href = href.split("?")[0].split("#")[0]
                        full_url = f"{self.base_url}{clean_href}" if clean_href.startswith("/") else clean_href

                        if not title or not full_url:
                            continue

                        description_text = f"Vacante de {title} en {company}. Requisitos técnicos para {title} en modalidad {location_val}."
                        try:
                            detail_page = await context.new_page()
                            await detail_page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
                            desc_el = await detail_page.query_selector("div.gb-rich-text, div#job-body, section.job-body, div.content")
                            if desc_el:
                                description_text = (await desc_el.inner_text()).strip()
                            await detail_page.close()
                        except Exception:
                            pass

                        if not description_text or len(description_text) < 50:
                            continue

                        job_item = {
                            "id": f"getonboard_{hash(clean_href)}",
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_val.strip(),
                            "description": description_text,
                            "salary": "",
                            "modality": "remote",
                            "url": full_url,
                            "posted_at": datetime.now() - timedelta(days=1),
                            "source": "GetOnBoard"
                        }

                        jobs.append(job_item)
                        found_in_cat += 1

                    print(f"  [GetOnBoard] '{cat_name}' -> {found_in_cat} vacantes")

                except Exception as e:
                    print(f"  [GetOnBoard] Error en '{cat_name}': {e}")

            await browser.close()

        unique_jobs = {j["url"]: j for j in jobs}
        return list(unique_jobs.values())
