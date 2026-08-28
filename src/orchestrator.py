import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config.settings import settings
from src.scrapers.computrabajo import ComputrabajoPlaywrightScraper
from src.scrapers.indeed import IndeedPlaywrightScraper
from src.scrapers.linkedin import LinkedInPlaywrightScraper
from src.scrapers.occ import OCCPlaywrightScraper
from src.scrapers.getonboard import GetOnBoardPlaywrightScraper
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.filters import (
    should_include_job,
    is_spanish_description,
    is_english_description,
    is_foreign_country_job,
    is_disallowed_non_software_role,
    detect_job_modality
)
from src.llm.triage import AITriageAgent
from src.notifier.telegram import TelegramNotifier
from src.notifier.email_sender import EmailNotifier
from src.notifier.report_generator import ReportGenerator

console = Console()

class JobAgentOrchestrator:
    """
    Orquestador Central de Búsqueda de Empleo, Triaje con IA y Alertas Multicanal.
    Central Orchestrator for Multi-Platform Job Scraping, AI Triage & Notifications.
    """

    def __init__(self):
        self.scrapers_pool = {
            "Computrabajo": ComputrabajoPlaywrightScraper(),
            "Indeed": IndeedPlaywrightScraper(),
            "LinkedIn": LinkedInPlaywrightScraper(),
            "OCCMundial": OCCPlaywrightScraper(),
            "GetOnBoard": GetOnBoardPlaywrightScraper(),
            "RemoteOK": RemoteOKScraper()
        }
        self.triage_agent = AITriageAgent()
        self.telegram_notifier = TelegramNotifier()
        self.email_notifier = EmailNotifier()
        self.report_generator = ReportGenerator()
        self.processed_file = settings.PROCESSED_JOBS_PATH
        self.processed_urls = self._load_processed_urls()

    def _load_processed_urls(self) -> set:
        if self.processed_file.exists():
            try:
                with open(self.processed_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data) if isinstance(data, list) else set()
            except Exception:
                return set()
        return set()

    def _save_processed_urls(self):
        try:
            self.processed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.processed_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_urls), f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[bold red]Error al guardar processed_jobs.json:[/bold red] {e}")

    def _mark_as_processed(self, job: Dict[str, Any]):
        url = job.get("url")
        job_id = job.get("id")
        if url:
            clean_url = url.split("?")[0].split("#")[0]
            self.processed_urls.add(clean_url)
        if job_id:
            self.processed_urls.add(str(job_id))
        self._save_processed_urls()

    async def run(
        self,
        keywords: List[str] = None,
        max_hours: float = 72.0,
        selected_platforms: Optional[List[str]] = None,
        modality_pref: str = "Remoto y Presencial en mi Ciudad",
        user_location: str = "Ensenada, Tijuana, Baja California",
        min_salary_relocate: float = 30000.0,
        english_level: str = "Español / Básico",
        enable_telegram: bool = True,
        enable_email: bool = False
    ):
        """
        Ejecuta el ciclo completo del pipeline de búsqueda con interfaz visual profesional.
        Runs the complete job hunter pipeline cycle with professional rich visual interface.
        """
        if not keywords:
            keywords = ["Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend", "Software Engineer"]

        # Filtrar plataformas activas
        active_scrapers = []
        if selected_platforms:
            for p_name in selected_platforms:
                if p_name in self.scrapers_pool:
                    active_scrapers.append(self.scrapers_pool[p_name])
        if not active_scrapers:
            active_scrapers = list(self.scrapers_pool.values())

        # Panel de inicio
        console.print(
            Panel(
                f"[bold cyan]Términos de búsqueda:[/bold cyan] {len(keywords)} variantes\n"
                f"[bold cyan]Ventana de tiempo:[/bold cyan] Últimas {int(max_hours)} horas (3 días)\n"
                f"[bold cyan]Modalidad preferida:[/bold cyan] {modality_pref}\n"
                f"[bold cyan]Ubicación local:[/bold cyan] {user_location}\n"
                f"[bold cyan]Nivel de idioma:[/bold cyan] {english_level}\n"
                f"[bold cyan]Plataformas activas:[/bold cyan] {len(active_scrapers)}\n"
                f"[bold cyan]Canal Telegram:[/bold cyan] {'[bold green]Activo[/bold green]' if enable_telegram else '[dim]Inactivo[/dim]'}\n"
                f"[bold cyan]Canal Email:[/bold cyan] {'[bold green]Activo[/bold green]' if enable_email else '[dim]Inactivo[/dim]'}",
                title=f"[bold green]AUTO JOB HUNTER AI v6.0 (UNIVERSAL)[/bold green] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                border_style="cyan"
            )
        )

        # ============================================================
        # FASE 1: SCRAPING PARALELO SIMULTANEO
        # ============================================================
        console.print(f"\n[bold yellow]Fase 1: Extracción en {len(active_scrapers)} plataformas en paralelo...[/bold yellow]\n")

        async def _run_scraper_safe(scraper):
            name = scraper.__class__.__name__.replace("PlaywrightScraper", "").replace("Scraper", "")
            try:
                res = await scraper.fetch_jobs(
                    keywords=keywords,
                    max_hours=max_hours,
                    user_location=user_location
                )
                return name, res
            except Exception as e:
                console.print(f"  [bold red]✖ Error en scraper {name}:[/bold red] {e}")
                return name, []

        tasks = [_run_scraper_safe(s) for s in active_scrapers]
        all_results = await asyncio.gather(*tasks)

        all_raw_jobs = []
        plat_table = Table(title="Resultados de Extracción por Plataforma", border_style="blue")
        plat_table.add_column("Plataforma", style="bold white")
        plat_table.add_column("Vacantes Extraídas", justify="center", style="bold cyan")
        
        for name, r in all_results:
            all_raw_jobs.extend(r)
            plat_table.add_row(name, str(len(r)))

        console.print("\n")
        console.print(plat_table)

        # ============================================================
        # FASE 2: DEDUPLICACION INICIAL
        # ============================================================
        unique_jobs_map = {}
        for j in all_raw_jobs:
            clean_url = j.get("url", "").split("?")[0].split("#")[0]
            unique_key = clean_url if clean_url else f"{j.get('source')}_{j.get('id')}"
            if unique_key not in unique_jobs_map:
                unique_jobs_map[unique_key] = j

        unique_jobs = list(unique_jobs_map.values())

        # ============================================================
        # FASE 3: DESCARTAR YA PROCESADAS
        # ============================================================
        unprocessed = []
        already_processed_count = 0
        for j in unique_jobs:
            clean_url = j.get("url", "").split("?")[0].split("#")[0]
            if clean_url in self.processed_urls or j.get("url") in self.processed_urls or j.get("id") in self.processed_urls:
                already_processed_count += 1
            else:
                unprocessed.append(j)

        # ============================================================
        # FASE 3.5: EXTRACCIÓN DE DESCRIPCIONES COMPLETAS (WEB SCRAPING REAL)
        # ============================================================
        if unprocessed:
            console.print(f"\n[bold cyan]Fase 1.5: Extracción de Descripciones Completas Reales ({len(unprocessed)} vacantes)...[/bold cyan]")
            from src.scrapers.enricher import JobDetailEnricher
            enricher = JobDetailEnricher(concurrency=8)
            unprocessed = await enricher.enrich_all(unprocessed)

        # ============================================================
        # FASE 4: FILTROS PRELIMINARES POR CODIGO
        # ============================================================
        candidate_jobs = []
        discarded_onsite = 0
        discarded_support = 0

        for j in unprocessed:
            t = j.get("title", "")
            d = j.get("description", "")
            loc = j.get("location", "")
            url = j.get("url", "")
            src = j.get("source", "")
            modality_field = str(j.get("modality", "")).lower()

            # 1. Descartar países extranjeros
            if is_foreign_country_job(loc, url):
                discarded_onsite += 1
                self._mark_as_processed(j)
                continue

            # 2. Descartar puestos no relacionados a software
            if is_disallowed_non_software_role(t, d):
                discarded_support += 1
                self._mark_as_processed(j)
                continue

            # 3. Validación de modalidad y ubicación
            local_keys = [k.strip() for k in user_location.replace(";", ",").split(",") if k.strip()]
            code_modality = detect_job_modality(j, user_local_keywords=local_keys)

            if modality_pref == "Solo Remoto":
                if code_modality != "remote":
                    discarded_onsite += 1
                    self._mark_as_processed(j)
                    continue

            elif modality_pref == "Remoto y Presencial en mi Ciudad":
                if code_modality in ["onsite_relocate", "hybrid"]:
                    if not any(k.lower() in loc.lower() for k in local_keys):
                        discarded_onsite += 1
                        self._mark_as_processed(j)
                        continue

            # 4. Validación de idioma si el usuario pidió solo español
            is_spanish_only = "español" in english_level.lower() or "espanol" in english_level.lower() or "básico" in english_level.lower() or "basico" in english_level.lower()
            if is_spanish_only and is_english_description(d, t):
                discarded_support += 1
                self._mark_as_processed(j)
                continue

            candidate_jobs.append(j)

        # ============================================================
        # FASE 5: TRIAJE CON INTELIGENCIA ARTIFICIAL
        # ============================================================
        console.print(f"\n[bold yellow]Fase 2: Triaje y Verificación con IA ({len(candidate_jobs)} candidatas)...[/bold yellow]\n")

        target_roles_summary = ", ".join(keywords[:6])

        async def _triage_single(job_obj):
            res = await self.triage_agent.evaluate_job(
                job_obj,
                user_english_level=english_level,
                user_location=user_location,
                target_roles=target_roles_summary
            )
            return job_obj, res

        triage_tasks = [_triage_single(j) for j in candidate_jobs]
        triage_results = await asyncio.gather(*triage_tasks)

        approved_jobs = []
        discarded_ai_role = 0

        for job_obj, triage_res in triage_results:
            if not triage_res.is_software_role:
                discarded_ai_role += 1
                self._mark_as_processed(job_obj)
                console.print(f"  [bold red][X] ROL NO SOFTWARE:[/bold red] '{job_obj['title'][:38]}' @ {job_obj['company']} [dim]({triage_res.rejection_reason})[/dim]")
                continue

            if not triage_res.is_match_for_user:
                discarded_ai_role += 1
                self._mark_as_processed(job_obj)
                console.print(f"  [bold yellow][!] NO COMPATIBLE:[/bold yellow] '{job_obj['title'][:38]}' @ {job_obj['company']} [dim]({triage_res.rejection_reason or triage_res.real_modality})[/dim]")
                continue

            # Filtrar por idioma si es requerido
            if is_spanish_only and triage_res.detected_language == "ENGLISH":
                discarded_ai_role += 1
                self._mark_as_processed(job_obj)
                console.print(f"  [bold yellow][!] DESCARTADA POR IDIOMA (INGLÉS):[/bold yellow] '{job_obj['title'][:38]}' @ {job_obj['company']}")
                continue

            # Actualizar campos enriquecidos por el Agente IA
            job_obj["company"] = triage_res.company_name
            job_obj["workplace_location"] = triage_res.workplace_location
            job_obj["real_modality"] = triage_res.real_modality
            job_obj["detected_language"] = triage_res.detected_language
            job_obj["match_percentage"] = triage_res.match_percentage
            job_obj["matched_skills"] = triage_res.matched_skills
            job_obj["missing_skills"] = triage_res.missing_skills
            job_obj["summary_highlight"] = triage_res.summary_highlight
            job_obj["role_category"] = triage_res.role_category

            console.print(f"  [bold green][OK] APROBADA POR IA ({triage_res.match_percentage}% MATCH):[/bold green] '{job_obj['title'][:35]}' @ [bold white]{job_obj['company'][:22]}[/bold white] [cyan]({triage_res.workplace_location})[/cyan]")
            approved_jobs.append(job_obj)

        # Ordenar vacantes aprobadas por compatibilidad (mayor a menor)
        approved_jobs.sort(key=lambda x: x.get("match_percentage", 0), reverse=True)

        # Separar por idioma de descripcion
        spanish_jobs = [j for j in approved_jobs if j.get("detected_language") == "SPANISH" or is_spanish_description(j.get("description", "") or j.get("title", ""))]
        english_jobs = [j for j in approved_jobs if j not in spanish_jobs]
        ordered_approved_jobs = spanish_jobs + english_jobs

        # ============================================================
        # TABLA DE RESUMEN EJECUTIVO FINAL
        # ============================================================
        summary_table = Table(title="Resumen de Búsqueda y Filtrado Inteligente", border_style="green")
        summary_table.add_column("Métrica / Categoría", style="bold cyan")
        summary_table.add_column("Cantidad", justify="center", style="bold white")

        summary_table.add_row("Total Vacantes Extraídas", str(len(all_raw_jobs)))
        summary_table.add_row("Vacantes Únicas", str(len(unique_jobs)))
        summary_table.add_row("Ya Procesadas / Duplicadas Omitidas", str(already_processed_count))
        summary_table.add_row("Nuevas Evaluadas por Filtros/IA", str(len(unprocessed)))
        summary_table.add_row("VACANTES APROBADAS Y ENTREGADAS", f"[bold green]{len(ordered_approved_jobs)}[/bold green]")
        summary_table.add_row("  • Descripción en Español (Primeras)", f"[green]{len(spanish_jobs)}[/green]")
        summary_table.add_row("  • Descripción en Inglés (Al final)", f"[yellow]{len(english_jobs)}[/yellow]")
        summary_table.add_row("Descartadas por Filtros / IA", str(discarded_onsite + discarded_support + discarded_ai_role))

        console.print("\n")
        console.print(summary_table)

        if not ordered_approved_jobs:
            console.print("\n[bold yellow][INFO] No se encontraron vacantes nuevas en este periodo que cumplan con tus filtros.[/bold yellow]\n")
            return

        # ============================================================
        # FASE 6: GENERACIÓN DE REPORTES LOCALES (HTML + MARKDOWN)
        # ============================================================
        html_path, md_path = self.report_generator.generate_reports(
            jobs=ordered_approved_jobs,
            search_keywords=keywords,
            max_hours=max_hours,
            user_location=user_location
        )
        console.print(f"\n[bold green][OK] Reporte interactivo HTML generado:[/bold green] [cyan]{html_path}[/cyan]")
        console.print(f"[bold green][OK] Reporte Markdown digest generado:[/bold green] [cyan]{md_path}[/cyan]")

        # ============================================================
        # FASE 7: ENTREGA MULTICANAL (TELEGRAM + EMAIL)
        # ============================================================
        total_approved = len(ordered_approved_jobs)

        # 1. Enviar a Telegram
        if enable_telegram and self.telegram_notifier.is_configured():
            console.print(f"\n[bold green]Enviando {total_approved} alertas ejecutivas a tu Telegram...[/bold green]")
            for idx, job in enumerate(ordered_approved_jobs, 1):
                await self.telegram_notifier.send_job_alert(job, index=idx, total=total_approved)
                self._mark_as_processed(job)
                await asyncio.sleep(0.3)
            
            await self.telegram_notifier.send_final_summary(
                total_found=total_approved,
                search_terms=keywords,
                hours_window=max_hours
            )
            console.print("  [bold green][OK] Alertas entregadas exitosamente en Telegram.[/bold green]")

        # 2. Enviar por Correo Electrónico
        if enable_email and self.email_notifier.is_configured():
            console.print(f"\n[bold green]Enviando Digest HTML con {total_approved} vacantes a tu correo...[/bold green]")
            success, email_msg = self.email_notifier.send_jobs_digest(
                jobs=ordered_approved_jobs,
                search_title=f"{keywords[0]} & Tech Roles"
            )
            if success:
                console.print(f"  [bold green][OK][/bold green] {email_msg}")
            else:
                console.print(f"  [bold red][!][/bold red] {email_msg}")

        console.print(f"\n[bold green][OK] Búsqueda finalizada con éxito. Total entregadas: {total_approved}[/bold green]\n")
