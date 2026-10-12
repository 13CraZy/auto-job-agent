"""
🧪 SUITE DE PRUEBAS AUTOMATIZADAS - AUTO JOB HUNTER AI & AGENTE JEV
===================================================================
Prueba el 100% de la funcionalidad del pipeline en modo seco (Dry-Run):
1. Primitivos matemáticos de Jev (choice, score, noul, stemmer, softmax).
2. Motor JobJevEngine (System 1 + filtrado de rol, modalidad, idioma y stack).
3. Deduplicación indestructible de Indeed (?jk=).
4. Formateo y escape seguro HTML de Telegram.
5. Ciclo completo del Orquestador con Telegram MOCKEADO (0 mensajes enviados)
   y processed_jobs.json REAL 100% PROTEGIDO (sin quemar ninguna vacante).
===================================================================
"""

import sys
import os
import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Asegurar path raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.jev.primitives import (
    tokenize,
    normalize_text,
    get_stem,
    calculate_token_similarity,
    softmax,
    choice,
    score,
    noul,
    MODALITY_REJECTION_TRAPS,
    LANGUAGE_C1_TRAPS,
    DISALLOWED_ROLE_TRAPS
)
from src.jev.engine import JobJevEngine
from src.notifier.telegram import TelegramNotifier
from src.orchestrator import JobAgentOrchestrator
from config.settings import settings


class TestJevPrimitives(unittest.TestCase):
    """Pruebas de los primitivos matemáticos y lingüísticos de Jev."""

    def test_normalize_and_tokenize(self):
        text = "¡Desarrollador Full-Stack en React.js, Node.js y Python!"
        tokens = tokenize(text)
        self.assertIn("desarrollador", tokens)
        self.assertIn("full-stack", tokens)
        self.assertIn("react.js", tokens)
        self.assertIn("node.js", tokens)
        self.assertIn("python", tokens)
        self.assertNotIn("en", tokens)  # Stopword descartada
        self.assertNotIn("y", tokens)   # Stopword descartada

    def test_stemming(self):
        self.assertEqual(get_stem("desarrolladores"), get_stem("desarrollando"))
        self.assertEqual(get_stem("programador"), get_stem("programadora"))
        self.assertEqual(get_stem("engineering"), get_stem("engineer"))

    def test_token_similarity(self):
        prompt_tokens = tokenize("Buscamos un Ingeniero de Software Full Stack en Next.js")
        sim_high = calculate_token_similarity(prompt_tokens, "Full Stack Next.js Software")
        sim_low = calculate_token_similarity(prompt_tokens, "Chofer repartidor de comida")
        self.assertGreater(sim_high, 0.7)
        self.assertLess(sim_low, 0.1)

    def test_softmax(self):
        scores = [1.0, 2.0, 5.0]
        probs = softmax(scores)
        self.assertEqual(len(probs), 3)
        self.assertAlmostEqual(sum(probs), 1.0, places=4)
        self.assertGreater(probs[2], probs[1])
        self.assertGreater(probs[1], probs[0])

    def test_choice_primitive(self):
        criteria = {
            "REMOTE": "100% remoto desde casa home office trabajo a distancia",
            "ONSITE": "presencial en corporativo oficinas asistencia diaria",
            "HYBRID": "esquema hibrido 3 dias oficina 2 dias remoto"
        }
        res_label, conf, all_scores = choice("Vacante 100% Home Office permanente desde casa", criteria)
        self.assertEqual(res_label, "REMOTE")
        self.assertGreater(conf, 0.6)

    def test_score_primitive(self):
        target_skills = ["React", "Node.js", "TypeScript", "PostgreSQL", "Docker", "Python"]
        job_desc = "Requerimos desarrollador con experiencia sólida en React, Node.js, TypeScript y PostgreSQL."
        pct, conf, matched = score(job_desc, target_skills)
        self.assertGreaterEqual(pct, 65)
        self.assertIn("React", matched)
        self.assertIn("Node.js", matched)
        self.assertIn("TypeScript", matched)
        self.assertIn("PostgreSQL", matched)

    def test_noul_primitive(self):
        is_bad, conf, reason = noul("Se solicita ejecutivo de ventas telefónicas y telemarketing", DISALLOWED_ROLE_TRAPS)
        self.assertTrue(is_bad)
        self.assertGreater(conf, 0.9)

        is_c1, conf_c1, reason_c1 = noul("Bilingual C1 English is strictly required", LANGUAGE_C1_TRAPS)
        self.assertTrue(is_c1)


class TestJobJevEngine(unittest.IsolatedAsyncioTestCase):
    """Pruebas del motor de decisión System 1 JobJevEngine."""

    async def asyncSetUp(self):
        self.engine = JobJevEngine()

    async def test_approve_remote_fullstack(self):
        job = {
            "title": "Desarrollador Full Stack (React & Node.js)",
            "company": "Software Solutions MX",
            "location": "Remoto, México",
            "description": "Buscamos desarrollador Full Stack con conocimientos en TypeScript, React, Next.js y PostgreSQL. Esquema 100% Home Office.",
            "url": "https://example.com/job/fs",
            "source": "LinkedIn",
            "modality": "remote"
        }
        res = await self.engine.evaluate_job(job, modality_pref="Solo Remoto", user_english_level="Español / Básico")
        self.assertTrue(res.is_software_role)
        self.assertTrue(res.is_match_for_user)
        self.assertEqual(res.real_modality, "REMOTE")
        self.assertGreaterEqual(res.match_percentage, 65)
        self.assertIn("React", res.matched_skills)

    async def test_reject_sales_role(self):
        job = {
            "title": "Ejecutivo de Ventas y Prospección",
            "company": "Ventas y Call Center SA",
            "location": "Remoto",
            "description": "Llamadas en frío, cierre de ventas y prospección comercial.",
            "url": "https://example.com/job/sales",
            "source": "Computrabajo"
        }
        res = await self.engine.evaluate_job(job)
        self.assertFalse(res.is_software_role)
        self.assertFalse(res.is_match_for_user)

    async def test_reject_onsite_outside_user_city(self):
        job = {
            "title": "Desarrollador Backend Python",
            "company": "Banco Jalisco",
            "location": "Guadalajara, Jalisco",
            "description": "Trabajo 100% presencial en corporativo Guadalajara de lunes a viernes.",
            "url": "https://example.com/job/gdl",
            "source": "OCCMundial"
        }
        res = await self.engine.evaluate_job(
            job,
            modality_pref="Solo Remoto",
            user_location="Ensenada, Baja California"
        )
        self.assertFalse(res.is_match_for_user)
        self.assertEqual(res.real_modality, "ONSITE_RELOCATE")

    async def test_accept_onsite_in_user_city_guadalajara(self):
        job = {
            "title": "Desarrollador Backend Python",
            "company": "Tech GDL",
            "location": "Guadalajara, Jalisco",
            "description": "Desarrollo de microservicios con FastAPI y PostgreSQL. Esquema híbrido 2 días en oficina Zapopan.",
            "url": "https://example.com/job/gdl-hybrid",
            "source": "OCCMundial"
        }
        res = await self.engine.evaluate_job(
            job,
            modality_pref="Remoto y Presencial en mi Ciudad",
            user_location="Guadalajara, Jalisco"
        )
        self.assertTrue(res.is_match_for_user)
        self.assertEqual(res.real_modality, "ONSITE_LOCAL")

    async def test_accept_onsite_in_user_city_cdmx(self):
        job = {
            "title": "Ingeniero de Software Full Stack",
            "company": "Fintech Insurgentes",
            "location": "Ciudad de México, Polanco",
            "description": "Desarrollo con React y Node.js. Asistencia 3 días en oficina Polanco.",
            "url": "https://example.com/job/cdmx-polanco",
            "source": "Computrabajo"
        }
        res = await self.engine.evaluate_job(
            job,
            modality_pref="Remoto y Presencial en mi Ciudad",
            user_location="Ciudad de México, CDMX"
        )
        self.assertTrue(res.is_match_for_user)
        self.assertEqual(res.real_modality, "ONSITE_LOCAL")

    async def test_reject_advanced_english_for_basic_user(self):
        job = {
            "title": "Full Stack Engineer",
            "company": "US Staffing",
            "location": "Remoto",
            "description": "We require a full stack developer. Fluent English C1 is mandatory for daily standups.",
            "url": "https://example.com/job/c1",
            "source": "Indeed"
        }
        res = await self.engine.evaluate_job(job, user_english_level="Español / Básico")
        self.assertFalse(res.is_match_for_user)
        self.assertIn("inglés avanzado", res.rejection_reason.lower())

    async def test_reject_java_spring_boot_role(self):
        job = {
            "title": "Desarrollador Java Spring Boot",
            "company": "Enterprise Bank",
            "location": "Remoto",
            "description": "Buscamos Desarrollador Java Senior con experiencia en Spring Boot, Hibernate, microservicios y SQL.",
            "url": "https://example.com/job/java",
            "source": "Indeed"
        }
        res = await self.engine.evaluate_job(job)
        self.assertFalse(res.is_match_for_user)
        self.assertIn("incompatible", res.rejection_reason.lower())

    async def test_reject_dotnet_csharp_role(self):
        job = {
            "title": "Desarrollador .NET C# Sr",
            "company": "Corporativo Seguros",
            "location": "Remoto",
            "description": "Experiencia indispensable en C#, .NET Core, ASP.NET y Entity Framework.",
            "url": "https://example.com/job/dotnet",
            "source": "Computrabajo"
        }
        res = await self.engine.evaluate_job(job)
        self.assertFalse(res.is_match_for_user)
        self.assertIn("incompatible", res.rejection_reason.lower())

    async def test_accept_angular_typescript_role(self):
        job = {
            "title": "Desarrollador Frontend Angular",
            "company": "SaaS Platform LATAM",
            "location": "Remoto",
            "description": "Desarrollo con Angular 17+, TypeScript, Signals, Tailwind CSS y consumo de APIs REST.",
            "url": "https://example.com/job/angular",
            "source": "LinkedIn"
        }
        res = await self.engine.evaluate_job(job)
        self.assertTrue(res.is_match_for_user)
        self.assertTrue(any("angular" in s.lower() for s in res.matched_skills))
        self.assertGreaterEqual(res.match_percentage, 65)

    async def test_accept_python_fastapi_role(self):
        job = {
            "title": "Backend Developer Python",
            "company": "Fintech Solutions",
            "location": "Remoto",
            "description": "Construcción de APIs con Python, FastAPI, PostgreSQL y Docker.",
            "url": "https://example.com/job/python-fastapi",
            "source": "GetOnBoard"
        }
        res = await self.engine.evaluate_job(job)
        self.assertTrue(res.is_match_for_user)
        self.assertIn("Python", res.matched_skills)
        self.assertGreaterEqual(res.match_percentage, 70)


class TestIndeedDeduplication(unittest.TestCase):
    """Verifica que la deduplicación de Indeed no colapse a /rc/clk."""

    def setUp(self):
        self.orchestrator = JobAgentOrchestrator()

    def test_indeed_unique_keys_dont_collide(self):
        indeed_jobs = [
            {"id": "indeed_101", "url": "https://mx.indeed.com/rc/clk?jk=101&bb=abc", "source": "Indeed", "title": "Dev 1", "company": "Co 1"},
            {"id": "indeed_102", "url": "https://mx.indeed.com/rc/clk?jk=102&bb=def", "source": "Indeed", "title": "Dev 2", "company": "Co 2"},
            {"id": "indeed_103", "url": "https://mx.indeed.com/rc/clk?jk=103&bb=ghi", "source": "Indeed", "title": "Dev 3", "company": "Co 3"},
            {"id": "", "url": "https://mx.indeed.com/rc/clk?jk=104", "source": "Indeed", "title": "Dev 4", "company": "Co 4"},
            {"id": "indeed_105", "url": "https://mx.indeed.com/viewjob?jk=105", "source": "Indeed", "title": "Dev 5", "company": "Co 5"},
        ]

        keys = [self.orchestrator._get_clean_job_key(j) for j in indeed_jobs]
        
        # Ninguna clave debe ser el genérico https://mx.indeed.com/rc/clk
        for k in keys:
            self.assertNotEqual(k, "https://mx.indeed.com/rc/clk")
            self.assertTrue(k.startswith("indeed_"))

        # Todas las claves deben ser únicas
        self.assertEqual(len(set(keys)), len(indeed_jobs))


class TestTelegramNotifierIsolated(unittest.IsolatedAsyncioTestCase):
    """Prueba el notificador de Telegram con HTTP mockeado (sin enviar alertas reales)."""

    async def test_html_escaping_and_card_structure(self):
        notifier = TelegramNotifier()
        
        malicious_job = {
            "title": "Backend <Dev> & 'Architect' _Node.js_",
            "company": "Tech & Solutions <Co>",
            "location": "Remoto",
            "salary": "$40,000 & prestaciones",
            "url": "https://example.com/job?id=123&ref=test",
            "description": "Stack: TypeScript_v5, <b>React</b> & C# con _snake_case_ y *asteriscos*.",
            "source": "Indeed",
            "match_percentage": 95,
            "matched_skills": ["TypeScript", "Node.js"],
            "summary_highlight": "Match alto & 100% seguro."
        }

        # Mockear cliente HTTP para interceptar el payload exacto
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            result = await notifier.send_job_alert(malicious_job, index=1, total=1)
            self.assertTrue(result)
            self.assertEqual(mock_post.call_count, 1)

            # Verificar contenido del payload enviado
            call_kwargs = mock_post.call_args.kwargs
            sent_json = call_kwargs["json"]
            self.assertEqual(sent_json["parse_mode"], "HTML")
            text = sent_json["text"]

            # Verificar que caracteres peligrosos fueron escapados adecuadamente
            self.assertIn("&lt;Dev&gt;", text)
            self.assertIn("Tech &amp; Solutions &lt;Co&gt;", text)
            self.assertIn("&lt;b&gt;React&lt;/b&gt;", text)
            self.assertIn("TypeScript_v5", text)  # El guión bajo no rompe en HTML
            self.assertNotIn("<script>", text)


class TestOrchestratorPipelineDryRun(unittest.IsolatedAsyncioTestCase):
    """
    Simulación completa End-to-End del pipeline del orquestador:
    - Telegram MOCKEADO (0 mensajes reales a Telegram).
    - processed_jobs.json REAL 100% PROTEGIDO (usando archivo temporal aislado).
    - Comprueba que las vacantes no se queman y quedan disponibles para la ejecución real.
    """

    async def asyncSetUp(self):
        # Crear un archivo temporal aislado para procesados de prueba
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_processed_path = Path(self.temp_dir.name) / "test_processed_jobs.json"
        
        # Archivo real de processed_jobs.json para verificar que NO cambia
        self.real_processed_path = settings.PROCESSED_JOBS_PATH
        if self.real_processed_path.exists():
            with open(self.real_processed_path, "r", encoding="utf-8") as f:
                self.real_processed_initial = f.read()
        else:
            self.real_processed_initial = ""

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_e2e_pipeline_dry_run_isolated(self):
        orchestrator = JobAgentOrchestrator()
        
        # 1. AISLAR processed_jobs.json hacia el archivo temporal
        orchestrator.processed_file = self.temp_processed_path
        orchestrator.processed_urls = set()

        # 2. MOCKEAR Telegram Notifier al 100%
        sent_telegram_alerts = []
        sent_summaries = []

        async def mock_send_alert(job, index=1, total=1):
            sent_telegram_alerts.append(job)
            return True

        async def mock_send_summary(total_found, search_terms, hours_window):
            sent_summaries.append({"total": total_found, "terms": search_terms, "hours": hours_window})
            return True

        orchestrator.telegram_notifier.send_job_alert = AsyncMock(side_effect=mock_send_alert)
        orchestrator.telegram_notifier.send_final_summary = AsyncMock(side_effect=mock_send_summary)

        # 3. MOCKEAR los scrapers para inyectar un lote sintético representativo de 7 días
        synthetic_raw_jobs = [
            {
                "id": "indeed_jk_9991",
                "title": "Desarrollador Full Stack React y Node.js",
                "company": "Empresa Tech Alpha",
                "location": "Remoto, México",
                "description": "Buscamos Desarrollador Full Stack con TypeScript, React y Node.js para proyecto 100% Remoto nacional.",
                "url": "https://mx.indeed.com/rc/clk?jk=9991",
                "source": "Indeed",
                "modality": "remote"
            },
            {
                "id": "indeed_jk_9992",
                "title": "Backend Developer Python FastAPI",
                "company": "Cloud Services LATAM",
                "location": "Desde Casa",
                "description": "Desarrollo de microservicios con FastAPI, PostgreSQL y Docker. 100% trabajo a distancia.",
                "url": "https://mx.indeed.com/rc/clk?jk=9992",
                "source": "Indeed",
                "modality": "remote"
            },
            {
                "id": "ct_101",
                "title": "Ejecutivo Telefónico de Ventas",
                "company": "Call Center Corp",
                "location": "Remoto",
                "description": "Venta de seguros y servicios financieros vía telefónica.",
                "url": "https://mx.computrabajo.com/oferta-sales-101",
                "source": "Computrabajo",
                "modality": "remote"
            },
            {
                "id": "li_201",
                "title": "Desarrollador Java Spring Onsite",
                "company": "Consultoría Monterrey",
                "location": "Monterrey, Nuevo León",
                "description": "Presencial obligatorio en San Pedro Garza García, Monterrey.",
                "url": "https://mx.linkedin.com/jobs/view/201",
                "source": "LinkedIn",
                "modality": "onsite"
            }
        ]

        # Inyectar scraper mock que retorna nuestro lote
        mock_scraper = MagicMock()
        mock_scraper.fetch_jobs = AsyncMock(return_value=synthetic_raw_jobs)
        orchestrator.scrapers_pool = {"MockPlatform": mock_scraper}

        # 4. EJECUTAR EL PIPELINE COMPLETO
        await orchestrator.run(
            keywords=["Desarrollador Full Stack", "Backend Developer"],
            max_hours=168.0,
            selected_platforms=["MockPlatform"],
            modality_pref="Solo Remoto",
            user_location="Ensenada, Baja California",
            english_level="Español / Básico",
            enable_telegram=True,
            enable_email=False
        )

        # 5. VERIFICACIONES DE ÉXITO
        # a) Deben haberse aprobado 2 vacantes de software remoto (Alpha y Cloud Services)
        # y descartado 2 (Ventas por rol no-software, y Monterrey por presencial foráneo)
        self.assertEqual(len(sent_telegram_alerts), 2)
        approved_titles = [j["title"] for j in sent_telegram_alerts]
        self.assertIn("Desarrollador Full Stack React y Node.js", approved_titles)
        self.assertIn("Backend Developer Python FastAPI", approved_titles)

        # b) Se debe haber llamado a send_final_summary con total 2 y ventana 168 horas
        self.assertEqual(len(sent_summaries), 1)
        self.assertEqual(sent_summaries[0]["total"], 2)
        self.assertEqual(sent_summaries[0]["hours"], 168.0)

        # c) processed_jobs.json REAL NO DEBE HABERSE MODIFICADO EN ABSOLUTO
        if self.real_processed_path.exists():
            with open(self.real_processed_path, "r", encoding="utf-8") as f:
                real_processed_current = f.read()
            self.assertEqual(real_processed_current, self.real_processed_initial,
                             "¡ALERTA! El archivo processed_jobs.json real fue modificado durante el test.")

        # d) Las vacantes procesadas durante el test quedaron en el archivo temporal, no en el real
        self.assertTrue(self.temp_processed_path.exists())
        with open(self.temp_processed_path, "r", encoding="utf-8") as f:
            temp_data = json.load(f)
        self.assertIn("indeed_9991", temp_data)
        self.assertIn("indeed_9992", temp_data)


if __name__ == "__main__":
    unittest.main()
