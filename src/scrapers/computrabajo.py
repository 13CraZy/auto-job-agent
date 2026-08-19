import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import quote
from playwright.async_api import async_playwright

def clean_computrabajo_company(text: str) -> str:
    """
    Limpia el nombre de la empresa eliminando calificaciones, estrellas y conteo de evaluaciones.
    Cleans company name removing ratings, stars, and evaluation counts.
    """
    if not text:
        return "Empresa Confidencial (Software)"
    text = re.sub(r'\b\d+[\.,]\d+\b', '', text)
    text = re.sub(r'\(?\d+\s*evaluaciones\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[★☆⭐]+', '', text)
    text = re.sub(r'\bPostular\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip(' -•,\n\r')
    if not text or text == "Empresa México" or "evaluacion" in text.lower():
        return "Empresa Confidencial (Software)"
    return text

def clean_computrabajo_location(text: str) -> str:
    """
    Limpia el texto de ubicacion eliminando residuos de calificaciones y texto publicitario.
    Cleans location text removing rating residues and ad text.
    """
    if not text:
        return "México"
    text = re.sub(r'\b\d+[\.,]\d+\b', '', text)
    text = re.sub(r'\(?\d+\s*evaluaciones\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[★☆⭐]+', '', text)
    text = re.sub(r'\bPostular\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip(' -•,\n\r')
    return text if text else "México"

class ComputrabajoPlaywrightScraper:
    """
    Scraper optimizado para mx.computrabajo.com con soporte nativo para 'Desde Casa' y 'Baja California'.
    Optimized Computrabajo scraper querying native 'Desde Casa' (100% remote) and 'Baja California' routes.
    """

    def __init__(self):
        self.base_url = "https://mx.computrabajo.com"

    async def fetch_jobs(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        if not keywords:
            keywords = ["Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend", "Software Engineer"]

        jobs = []
        search_terms = keywords[:4]

        # Rutas estrategicas: 100% Desde Casa, Local en Baja California, y Busqueda Remoto general
        query_configs = []
        for kw in search_terms:
            slug = kw.lower().replace(" ", "-").replace("ñ", "n").replace("desarrollador-", "")
            kw_encoded = quote(kw)
            
            query_configs.append((f"{kw} [100% Desde Casa]", f"{self.base_url}/trabajo-de-{slug}-en-desde-casa", "remote"))
            query_configs.append((f"{kw} [Baja California]", f"{self.base_url}/empleos-en-baja-california?q={kw_encoded}", "onsite_local"))
            query_configs.append((f"{kw} [Remoto General]", f"{self.base_url}/empleos-en-mexico?q={kw_encoded}+remoto", "remote"))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            # Bloquear imagenes y estilos pesados / Block heavy assets
            await context.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2,ttf,css,ico,webp}", lambda route: route.abort())
            page = await context.new_page()

            for label, url, default_modality in query_configs:
                found_in_query = 0
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                    await asyncio.sleep(0.4)

                    job_cards = await page.query_selector_all("article.box_offer, article[data-id]")

                    for card in job_cards[:15]:
                        link_el = await card.query_selector("h1 a, h2 a, a.js-o-link")
                        data_id = await card.get_attribute("data-id")

                        href = ""
                        if link_el:
                            href = await link_el.get_attribute("href") or ""

                        if not href or ("/ofertas-de-trabajo/" not in href and "/oferta-de-trabajo-" not in href):
                            continue

                        clean_href = href.split("#")[0].split("?")[0]
                        full_url = f"{self.base_url}{clean_href}" if clean_href.startswith("/") else clean_href
                        unique_id = data_id if data_id else clean_href.split("-")[-1]
                        job_key = f"computrabajo_{unique_id}"

                        title = (await link_el.inner_text()).strip() if link_el else label

                        # 1. Extraccion limpia de Empresa
                        raw_company = ""
                        comp_card_el = await card.query_selector("p.fs16 a, p.fc_base a, a[href*='/empresas/'], p.fs16, p.fc_base")
                        if comp_card_el:
                            raw_company = (await comp_card_el.inner_text()).strip()
                        company = clean_computrabajo_company(raw_company)

                        # 2. Extraccion de Parrafos del Card (Ubicacion, Modalidad, Salario)
                        paragraphs = await card.query_selector_all("p")
                        location = "México"
                        salary_text = ""
                        card_modality = default_modality

                        for p_el in paragraphs:
                            txt = (await p_el.inner_text()).strip()
                            if "$" in txt:
                                salary_text = txt
                            if any(st in txt.lower() for st in ["ciudad de méxico", "baja california", "jalisco", "nuevo león", "querétaro", "puebla", "yucatán", "tijuana", "ensenada", "mexicali", "guadalajara", "monterrey", "desde casa", "remoto"]):
                                location = clean_computrabajo_location(txt)
                            if "presencial y remoto" in txt.lower() or "híbrido" in txt.lower() or "hibrido" in txt.lower():
                                card_modality = "hybrid"
                            elif "desde casa" in txt.lower() or "100% remoto" in txt.lower() or "home office" in txt.lower():
                                card_modality = "remote"
                            elif "presencial" in txt.lower() and card_modality != "remote":
                                card_modality = "onsite"

                        # 3. Snippet
                        snippet_el = await card.query_selector("p.mb10, p.fs14")
                        snippet_text = (await snippet_el.inner_text()).strip() if snippet_el else ""

                        description_text = snippet_text if len(snippet_text) > 40 else f"Vacante de {title} en {company}. Ubicación de empresa: {location}. Modalidad: {card_modality}."

                        job_item = {
                            "id": job_key,
                            "title": title,
                            "company": company,
                            "location": location,
                            "description": description_text,
                            "salary": salary_text,
                            "modality": card_modality,
                            "url": full_url,
                            "posted_at": datetime.now() - timedelta(days=1),
                            "source": "Computrabajo"
                        }

                        jobs.append(job_item)
                        found_in_query += 1

                    print(f"  [Computrabajo] {label} -> {found_in_query} vacantes")

                except Exception as e:
                    print(f"  [Computrabajo] Error en {label}: {e}")

            await browser.close()

        unique_jobs = {j["id"]: j for j in jobs}
        return list(unique_jobs.values())
