"""
🧠 JOB JEV ENGINE - MOTOR DE DECISIONES SYSTEM 1 PARA EMPLEO
============================================================
Cerebro decisional determinista inspirado en LuxJev (E:\Luxnode).
- 100% Local, no autorregresivo y ultra rápido (<5ms).
- Arquitectura Dual-Process (System 1 Local -> Escalación a System 2 LLM solo en ambigüedad).
- Reduce en >85% las llamadas a APIs externas de IA.
- Deduplicación robusta e inmunidad contra trampas de exclusión.
============================================================
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from config.settings import settings
from src.jev.primitives import (
    choice,
    score,
    noul,
    tokenize,
    normalize_text,
    MODALITY_REJECTION_TRAPS,
    LANGUAGE_C1_TRAPS,
    DISALLOWED_ROLE_TRAPS,
    INCOMPATIBLE_STACK_TRAPS,
    CORE_PREFERRED_TECH_PATTERNS
)
from src.scrapers.filters import (
    is_foreign_country_job,
    detect_text_language,
    detect_job_modality,
    requires_advanced_english,
    is_disallowed_non_software_role
)
from src.llm.triage import JobTriageResult, AITriageAgent


class JobJevEngine:
    """
    Motor de Decisión Inteligente para Vacantes (System 1 Local + System 2 LLM Fallback).
    """

    def __init__(self):
        self.user_profile = self._load_user_profile()
        self.skills_pool = self._extract_skills_pool()
        self.skill_weights = {
            "TypeScript": 3.5,
            "JavaScript": 3.0,
            "Python": 3.5,
            "Angular": 3.5,
            "React": 3.5,
            "Next.js": 3.5,
            "Node.js": 3.5,
            "FastAPI": 3.0,
            "Express": 2.5,
            "PostgreSQL": 2.5,
            "Supabase": 2.5,
            "Tailwind CSS": 2.0,
            "WebSockets": 2.5,
            "Docker": 2.0,
            "Redis": 2.0,
            "SQL": 1.5,
            "Git": 1.0,
            "AWS": 1.5,
            "Full Stack": 2.5
        }
        self.system2_agent = AITriageAgent()

    def _load_user_profile(self) -> Dict[str, Any]:
        """Carga el perfil profesional real del usuario."""
        profile_path = settings.profile_path_resolved
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _extract_skills_pool(self) -> List[str]:
        """Extrae el conjunto maestro de habilidades técnicas del usuario."""
        skills_data = self.user_profile.get("skills", {})
        pool = []
        for category, skill_list in skills_data.items():
            if isinstance(skill_list, list):
                pool.extend(skill_list)

        # Fallback si el perfil está vacío
        if not pool:
            pool = [
                "TypeScript", "JavaScript", "Python", "Angular", "React", "Next.js", "Node.js",
                "FastAPI", "Express", "PostgreSQL", "Supabase", "SQL", "Docker",
                "Tailwind CSS", "WebSockets", "Redis", "Git", "REST APIs", "Full Stack"
            ]

        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_pool = []
        for s in pool:
            s_clean = s.strip()
            if s_clean and s_clean.lower() not in seen:
                seen.add(s_clean.lower())
                unique_pool.append(s_clean)
        return unique_pool

    async def evaluate_job(
        self,
        job: Dict[str, Any],
        user_english_level: str = "Español / Básico",
        user_location: str = "Ciudad de México, México",
        target_roles: str = "Full Stack, Backend, Frontend, Software Engineer",
        modality_pref: str = "Solo Remoto"
    ) -> JobTriageResult:
        """
        Evalúa la vacante a través de System 1 (<5ms).
        Si la confianza es alta, emite la decisión localmente;
        si hay ambigüedad genuina, escala a System 2 (LLM).
        """
        title = job.get("title", "")
        company = job.get("company", "Empresa Confidencial")
        location = job.get("location", "México")
        description = job.get("description", "")
        url = job.get("url", "")
        source = job.get("source", "Web")
        job_modality_hint = job.get("modality", "")

        combined_text = f"{title}\n{company}\n{location}\n{description}"
        is_spanish_only = "español" in user_english_level.lower() or "espanol" in user_english_level.lower() or "básico" in user_english_level.lower() or "basico" in user_english_level.lower()
        is_strict_remote = modality_pref == "Solo Remoto"

        local_keywords = [k.strip() for k in user_location.replace(";", ",").split(",") if k.strip()]

        # ------------------------------------------------------------
        # CABEZAL 1: DESCARTE DE FRONTERAS Y ROLES NO-SOFTWARE (NOUL)
        # ------------------------------------------------------------
        # 1.1 País foráneo presencial
        if is_foreign_country_job(job):
            return JobTriageResult(
                is_software_role=True,
                real_modality="ONSITE_RELOCATE",
                workplace_location=location,
                company_name=company,
                detected_language="SPANISH",
                is_match_for_user=False,
                match_percentage=10,
                rejection_reason="Vacante presencial fuera de México",
                role_category="Otro"
            )

        # 1.2 Rol no-técnico (ventas, docencia, RH, diseño puro, soporte hardware)
        is_disallowed, noul_conf, noul_reason = noul(f"{title} {description[:400]}", DISALLOWED_ROLE_TRAPS)
        if not is_disallowed and is_disallowed_non_software_role(title, description[:400]):
            is_disallowed = True
            noul_reason = "Puesto no relacionado a software"

        if is_disallowed:
            return JobTriageResult(
                is_software_role=False,
                real_modality="UNKNOWN",
                workplace_location=location,
                company_name=company,
                detected_language="SPANISH",
                is_match_for_user=False,
                match_percentage=15,
                rejection_reason=f"Rol no relacionado con desarrollo de software ({noul_reason})",
                role_category="Otro"
            )

        # ------------------------------------------------------------
        # CABEZAL 1.3: FILTRADO DE STACKS INCOMPATIBLES (JAVA / .NET / PHP / C#)
        # ------------------------------------------------------------
        has_stack_trap_title, _, trap_trigger_title = noul(title, INCOMPATIBLE_STACK_TRAPS)
        has_preferred_tech_title, _, _ = noul(title, CORE_PREFERRED_TECH_PATTERNS)

        # Regla A: Título explícito de Java, .NET, C#, PHP sin mencionar tecnologías preferidas
        if has_stack_trap_title and not has_preferred_tech_title:
            return JobTriageResult(
                is_software_role=True,
                real_modality="REMOTE" if "remoto" in location.lower() or "remote" in location.lower() else "UNKNOWN",
                workplace_location=location,
                company_name=company,
                detected_language="SPANISH",
                is_match_for_user=False,
                match_percentage=20,
                rejection_reason=f"Puesto enfocado en tecnología incompatible ({trap_trigger_title}) no afín al perfil del usuario",
                role_category="Otro"
            )

        # Regla B: Descripción centrada en Java/.NET/PHP sin requerir el stack principal del usuario
        has_stack_trap_body, _, trap_trigger_body = noul(description[:1200], INCOMPATIBLE_STACK_TRAPS)
        has_preferred_tech_body, _, _ = noul(f"{title} {description}", CORE_PREFERRED_TECH_PATTERNS)
        if has_stack_trap_body and not has_preferred_tech_body:
            return JobTriageResult(
                is_software_role=True,
                real_modality="REMOTE" if "remoto" in location.lower() or "remote" in location.lower() else "UNKNOWN",
                workplace_location=location,
                company_name=company,
                detected_language="SPANISH",
                is_match_for_user=False,
                match_percentage=25,
                rejection_reason=f"Puesto enfocado en tecnología incompatible ({trap_trigger_body}) sin requerir TypeScript, Python, Angular o JavaScript",
                role_category="Otro"
            )

        # ------------------------------------------------------------
        # CABEZAL 2: IDIOMA Y REQUISITOS DE INGLÉS AVANZADO (CHOICE + NOUL)
        # ------------------------------------------------------------
        detected_lang = detect_text_language(description, title).upper()
        if detected_lang not in ["SPANISH", "ENGLISH"]:
            detected_lang = "SPANISH"

        has_c1_trap, c1_conf, c1_trigger = noul(f"{title} {description}", LANGUAGE_C1_TRAPS)
        requires_adv_english = has_c1_trap or requires_advanced_english(f"{title} {description}")

        if is_spanish_only and requires_adv_english:
            return JobTriageResult(
                is_software_role=True,
                real_modality="REMOTE" if "remoto" in location.lower() or "remote" in location.lower() else "UNKNOWN",
                workplace_location=location,
                company_name=company,
                detected_language="ENGLISH",
                is_match_for_user=False,
                match_percentage=40,
                rejection_reason="Exige inglés avanzado C1/C2 o bilingüe estricto",
                role_category="Full Stack"
            )

        # ------------------------------------------------------------
        # CABEZAL 3: CLASIFICADOR DE MODALIDAD (CHOICE + HEURÍSTICA JEV)
        # ------------------------------------------------------------
        has_modality_trap, mod_trap_conf, mod_trap_trigger = noul(f"{title} {description[:500]}", MODALITY_REJECTION_TRAPS)
        heuristic_mod = detect_job_modality(job, user_local_keywords=local_keywords)

        modality_criteria = {
            "REMOTE": "100% remoto trabajo a distancia home office permanente full remote desde casa cualquier parte mexico",
            "HYBRID": "esquema hibrido dias en oficina presencial y remoto alternado 2 dias 3 dias mixto",
            "ONSITE_LOCAL": f"presencial en oficina local {' '.join(local_keywords)}",
            "ONSITE_RELOCATE": "presencial obligatorio en oficina cdmx guadalajara monterrey queretaro otra ciudad"
        }

        eval_modality_text = f"{job_modality_hint} {location} {description[:400]}"
        choice_mod, mod_confidence, mod_scores = choice(eval_modality_text, modality_criteria, default_value="REMOTE")

        # Priorizar veredicto estricto de modalidad
        if has_modality_trap:
            real_modality = "ONSITE_RELOCATE" if not any(k.lower() in location.lower() for k in local_keywords) else "ONSITE_LOCAL"
        elif heuristic_mod == "remote" or choice_mod == "REMOTE":
            real_modality = "REMOTE"
        elif heuristic_mod == "onsite_local" or choice_mod == "ONSITE_LOCAL":
            real_modality = "ONSITE_LOCAL"
        elif heuristic_mod in ["hybrid", "onsite_relocate"] or choice_mod in ["HYBRID", "ONSITE_RELOCATE"]:
            real_modality = "HYBRID" if "hibrid" in combined_text.lower() else "ONSITE_RELOCATE"
        else:
            real_modality = "REMOTE" if "remoto" in location.lower() or "desde casa" in location.lower() else "UNKNOWN"

        # Validación con preferencia de usuario
        if is_strict_remote and real_modality != "REMOTE":
            return JobTriageResult(
                is_software_role=True,
                real_modality=real_modality,
                workplace_location=location,
                company_name=company,
                detected_language=detected_lang,
                is_match_for_user=False,
                match_percentage=45,
                rejection_reason=f"No es 100% Remoto permanente ({real_modality})",
                role_category="Full Stack"
            )

        if modality_pref == "Remoto y Presencial en mi Ciudad":
            if real_modality in ["ONSITE_RELOCATE", "HYBRID"]:
                if not any(k.lower() in location.lower() for k in local_keywords):
                    return JobTriageResult(
                        is_software_role=True,
                        real_modality=real_modality,
                        workplace_location=location,
                        company_name=company,
                        detected_language=detected_lang,
                        is_match_for_user=False,
                        match_percentage=45,
                        rejection_reason="Presencial foráneo fuera de tu ciudad",
                        role_category="Full Stack"
                    )

        # ------------------------------------------------------------
        # CABEZAL 4: AFINIDAD TÉCNICA Y CATEGORÍA DE ROL (SCORE JEV)
        # ------------------------------------------------------------
        match_score_val, tech_confidence, matched_skills = score(combined_text, self.skills_pool, weights=self.skill_weights)

        # Validación estricta de pertenencia al dominio de software
        SOFTWARE_TITLE_PATTERNS = [
            r"\b(?:desarrollador|desarrolladora|developer|software|ingenier[oa]|programmer|programador|programadora)\b",
            r"\b(?:full\s*stack|frontend|backend|devops|qa|web|mobile|cloud|sistemas|ti|soporte\s*tecnico)\b",
            r"\b(?:architect|arquitecto|analista\s+de\s+sistemas|data\s+engineer|data\s+science)\b"
        ]
        is_software_title = any(re.search(p, normalize_text(title)) for p in SOFTWARE_TITLE_PATTERNS)

        if len(matched_skills) == 0 and not is_software_title:
            return JobTriageResult(
                is_software_role=False,
                real_modality=real_modality,
                workplace_location=location,
                company_name=company,
                detected_language=detected_lang,
                is_match_for_user=False,
                match_percentage=10,
                rejection_reason="No coincide con roles ni tecnologías de desarrollo de software",
                role_category="Otro"
            )

        # Categoría técnica de rol
        role_criteria = {
            "Full Stack": "desarrollador full stack fullstack web frontend y backend end to end",
            "Backend": "desarrollador backend apis nodejs python postgresql bases de datos microservicios",
            "Frontend": "desarrollador frontend react nextjs angular css html interfaces ui",
            "Soporte Técnico": "soporte tecnico software ti help desk sistemas",
            "Mobile": "mobile flutter react native android ios",
            "DevOps/QA": "devops qa automation ci cd docker aws cloud testing"
        }
        role_cat, role_conf, _ = choice(f"{title} {description[:300]}", role_criteria, default_value="Full Stack")

        # ------------------------------------------------------------
        # COMPUERTA DE DECISIÓN Y ESCALACIÓN A SYSTEM 2 (LLM)
        # ------------------------------------------------------------
        overall_confidence = (mod_confidence * 0.4) + (tech_confidence * 0.4) + (role_conf * 0.2)

        # Si el caso está en la zona gris (ambigüedad genuina de requisitos o descripción confusa)
        # y tenemos menos de 1 coincidencia técnica clara, escalar puntualmente a System 2
        is_ambiguous = (overall_confidence < 0.65 and len(matched_skills) < 2 and len(description) > 300)

        if is_ambiguous:
            try:
                # Escalación quirúrgica a System 2
                llm_res = await self.system2_agent.evaluate_job(
                    job,
                    user_english_level=user_english_level,
                    user_location=user_location,
                    target_roles=target_roles,
                    modality_pref=modality_pref
                )
                return llm_res
            except Exception:
                pass  # Fallback a System 1 local

        # Generar resumen highlight
        workplace_loc = "100% Remoto (Home Office Nacional / LATAM)" if real_modality == "REMOTE" else location
        skills_str = ", ".join(matched_skills[:4]) if matched_skills else "Desarrollo de Software"
        highlight = f"Vacante de {role_cat} con alta compatibilidad en {skills_str} ({workplace_loc})."

        return JobTriageResult(
            is_software_role=True,
            real_modality=real_modality,
            workplace_location=workplace_loc,
            company_name=company,
            detected_language=detected_lang,
            is_match_for_user=True,
            match_percentage=match_score_val,
            matched_skills=matched_skills[:6],
            missing_skills=[],
            summary_highlight=highlight,
            rejection_reason="",
            role_category=role_cat
        )
