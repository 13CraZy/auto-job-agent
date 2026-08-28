import json
import re
import asyncio
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
from google import genai
from config.settings import settings

class JobTriageResult(BaseModel):
    """
    Modelo estructurado del resultado de evaluacion de triaje por IA con deteccion de modalidad, ubicacion y compatibilidad.
    Structured data model for AI job triage evaluation result including modality, location, and match score.
    """
    is_software_role: bool = Field(
        description="True si es desarrollo/ingenieria de software o soporte TI de software. False si es ventas, docencia, etc."
    )
    real_modality: Literal["REMOTE", "HYBRID", "ONSITE_LOCAL", "ONSITE_RELOCATE", "UNKNOWN"] = Field(
        default="REMOTE",
        description="Modalidad real: REMOTE (100% Home Office), HYBRID (Presencial y Remoto), ONSITE_LOCAL (En la ciudad/estado local), ONSITE_RELOCATE (Presencial foraneo)"
    )
    workplace_location: str = Field(
        default="100% Remoto (Home Office)",
        description="Ubicacion real donde se desempeña el trabajo"
    )
    company_name: str = Field(
        description="Nombre real limpio de la empresa sin estrellas ni evaluaciones"
    )
    detected_language: Literal["SPANISH", "ENGLISH"] = Field(
        default="SPANISH",
        description="Idioma principal en el que estan redactados los requisitos y actividades del puesto"
    )
    is_match_for_user: bool = Field(
        default=True,
        description="True solo si cumple con la modalidad, rol y preferencia de idioma del usuario"
    )
    match_percentage: int = Field(
        default=90,
        description="Porcentaje de compatibilidad técnica con el perfil (0 a 100)"
    )
    matched_skills: list = Field(
        default_factory=list,
        description="Lista de tecnologías o habilidades coincidentes encontradas en la oferta"
    )
    missing_skills: list = Field(
        default_factory=list,
        description="Lista de tecnologías secundarias o requerimientos adicionales no prioritarios"
    )
    summary_highlight: str = Field(
        default="",
        description="Resumen de 1-2 frases destacando lo más relevante del puesto y por qué encaja"
    )
    rejection_reason: str = Field(
        default="",
        description="Explicacion breve en espanol si es rechazado"
    )
    role_category: Literal["Backend", "Frontend", "Full Stack", "Soporte Técnico", "Mobile", "DevOps/QA", "Data/AI", "Otro"] = Field(
        default="Full Stack",
        description="Categoria tecnica principal del puesto"
    )

class AITriageAgent:
    """
    Agente de Triaje con IA con sistema de Failover Multiproveedor (Groq -> Gemini -> OpenRouter -> Heurístico Local).
    AI Job Triage Agent with multi-provider failover chain.
    """

    def __init__(self):
        self.semaphore = asyncio.Semaphore(4)

        # 1. Proveedor Groq (Llama-3.1-8B-Instant / Llama-3.3-70B) / Groq Provider
        self.groq_client = None
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_") and not settings.GROQ_API_KEY.startswith("gsk_your_"):
            try:
                self.groq_client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=settings.GROQ_API_KEY,
                    timeout=10.0
                )
            except Exception:
                self.groq_client = None

        # 2. Proveedor Gemini (Google GenAI) / Gemini Provider
        self.gemini_client = None
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") and not settings.GEMINI_API_KEY.startswith("AIzaSy_your_"):
            try:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                self.gemini_client = None

        # 3. Proveedor OpenRouter (Respaldo) / OpenRouter Backup Provider
        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_") and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-your_"):
            try:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    timeout=12.0,
                    default_headers={
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "AutoJobAgent"
                    }
                )
            except Exception:
                self.openrouter_client = None

    async def evaluate_job(
        self,
        job: Dict[str, Any],
        user_english_level: str = "Español / Básico",
        user_location: str = "Ensenada, Baja California",
        target_roles: str = "Full Stack, Backend, Frontend, Software Engineer"
    ) -> JobTriageResult:
        """
        Evalúa y clasifica de forma estricta la vacante analizando modalidad real, idioma y compatibilidad.
        Evaluates and strictly classifies job modality, language, and candidate match with concurrency control.
        """
        async with self.semaphore:
            title = job.get("title", "")
            company = job.get("company", "Empresa Confidencial")
            location = job.get("location", "México")
            description = job.get("description", "")
            source = job.get("source", "Web")
            job_modality_hint = job.get("modality", "")

            is_spanish_only_user = "español" in user_english_level.lower() or "espanol" in user_english_level.lower() or "básico" in user_english_level.lower() or "basico" in user_english_level.lower()

            prompt = f"""Eres un Evaluador y Reclutador Técnico Senior de Software.
Tu misión es clasificar esta vacante con CERO ERRORES y TOTAL PRECISIÓN:

1. IDIOMA REAL (detected_language):
   - "ENGLISH": Si el título, los requisitos o las responsabilidades están redactados en inglés (ej: 'Software Developer', 'Backend Engineer', 'Requirements', 'Responsibilities', 'Must have').
   - "SPANISH": ÚNICAMENTE si todos los requisitos y responsabilidades están redactados en español.

2. MODALIDAD REAL (real_modality):
   - "REMOTE": ÚNICAMENTE si es 100% Home Office / Remoto permanente desde cualquier parte de México sin requerir asistencia física a oficina.
   - "HYBRID": Si menciona esquema híbrido, días en oficina, esquema mixto, o 2-3 días presenciales.
   - "ONSITE_LOCAL": Si es presencial o híbrido en la ciudad del usuario ({user_location}).
   - "ONSITE_RELOCATE": Si es presencial o híbrido en otra ciudad fuera de {user_location} (ej: CDMX, Guadalajara, Monterrey, Querétaro, etc.) y NO es 100% desde casa permanente.

3. COMPATIBILIDAD CON EL CANDIDATO (is_match_for_user):
   - True SOLO SI:
     a) Es un rol técnico de Software/TI (is_software_role = true).
     b) Es 100% Remoto ("REMOTE") O Presencial en {user_location} ("ONSITE_LOCAL").
     {"c) detected_language es 'SPANISH' y NO exige inglés C1/C2." if is_spanish_only_user else "c) Aceptable en inglés o español."}
   - Si es Híbrido o Presencial en otra ciudad -> is_match_for_user = false.
   - {"Si está en inglés -> is_match_for_user = false." if is_spanish_only_user else ""}

OFERTA A EVALUAR:
- Título: {title}
- Empresa: {company}
- Ubicación indicada: {location}
- Fuente: {source}
- Pista de modalidad: {job_modality_hint}
- Descripción:
{description}

Devuelve ÚNICAMENTE un JSON válido con esta estructura:
{{
  "is_software_role": true,
  "real_modality": "REMOTE",
  "workplace_location": "100% Remoto (Home Office Nacional / LATAM)",
  "company_name": "Nombre limpio de la empresa",
  "detected_language": "SPANISH",
  "is_match_for_user": true,
  "match_percentage": 95,
  "matched_skills": ["React", "TypeScript", "Node.js"],
  "missing_skills": [],
  "summary_highlight": "Oportunidad 100% remota con enfoque en React.",
  "rejection_reason": "",
  "role_category": "Full Stack"
}}"""

            loop = asyncio.get_event_loop()

            # 1. Intentar con Groq / Try Groq
            if self.groq_client:
                for model_name in ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]:
                    try:
                        def _call_groq():
                            response = self.groq_client.chat.completions.create(
                                model=model_name,
                                messages=[
                                    {"role": "system", "content": "Eres un evaluador de vacantes que responde exclusivamente en JSON estructurado válido."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.1,
                                response_format={"type": "json_object"}
                            )
                            return response.choices[0].message.content

                        raw_text = await loop.run_in_executor(None, _call_groq)
                        data = json.loads(raw_text.strip())
                        return self._build_result_from_dict(data, location, company, is_spanish_only_user)
                    except Exception:
                        await asyncio.sleep(0.3)
                        continue

            # 2. Intentar con Google Gemini / Try Gemini
            if self.gemini_client:
                for gemini_model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                    try:
                        def _call_gemini():
                            response = self.gemini_client.models.generate_content(
                                model=gemini_model,
                                contents=prompt,
                                config={"response_mime_type": "application/json"}
                            )
                            return response.text

                        raw_text = await loop.run_in_executor(None, _call_gemini)
                        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        data = json.loads(cleaned)
                        return self._build_result_from_dict(data, location, company, is_spanish_only_user)
                    except Exception:
                        await asyncio.sleep(0.3)
                        continue

            # 3. Intentar con OpenRouter / Try OpenRouter
            if self.openrouter_client:
                try:
                    def _call_openrouter():
                        response = self.openrouter_client.chat.completions.create(
                            model="meta-llama/llama-3.1-8b-instruct",
                            messages=[
                                {"role": "system", "content": "Eres un asistente JSON estricto."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=700,
                            temperature=0.1
                        )
                        return response.choices[0].message.content

                    raw_text = await loop.run_in_executor(None, _call_openrouter)
                    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    data = json.loads(cleaned)
                    return self._build_result_from_dict(data, location, company, is_spanish_only_user)
                except Exception:
                    pass

            # 4. Fallback Heurístico Robusto / Robust Heuristic Fallback
            return self._heuristic_fallback(job, title, description, location, company, is_spanish_only_user, user_location)

    def _build_result_from_dict(
        self,
        data: dict,
        location: str,
        company: str,
        is_spanish_only_user: bool,
        title: str = "",
        description: str = ""
    ) -> JobTriageResult:
        from src.scrapers.filters import detect_text_language

        real_mod = str(data.get("real_modality", "REMOTE")).upper()
        if real_mod not in ["REMOTE", "HYBRID", "ONSITE_LOCAL", "ONSITE_RELOCATE", "UNKNOWN"]:
            real_mod = "REMOTE" if "remot" in str(data.get("real_modality", "")).lower() else "UNKNOWN"

        lang = str(data.get("detected_language", "")).upper()
        if lang not in ["SPANISH", "ENGLISH"]:
            lang = detect_text_language(description, title).upper()

        is_match = bool(data.get("is_match_for_user", True))
        if is_spanish_only_user and lang == "ENGLISH":
            is_match = False

        score = data.get("match_percentage", 90)
        try:
            score = max(50, min(99, int(score)))
        except Exception:
            score = 90

        role_cat = str(data.get("role_category", "Full Stack"))
        valid_cats = ["Backend", "Frontend", "Full Stack", "Soporte Técnico", "Mobile", "DevOps/QA", "Data/AI", "Otro"]
        if role_cat not in valid_cats:
            role_cat = "Full Stack"

        return JobTriageResult(
            is_software_role=bool(data.get("is_software_role", True)),
            real_modality=real_mod,
            workplace_location=data.get("workplace_location", location or "100% Remoto (Home Office)"),
            company_name=data.get("company_name", company),
            detected_language=lang,
            is_match_for_user=is_match,
            match_percentage=score,
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            summary_highlight=data.get("summary_highlight", ""),
            rejection_reason=data.get("rejection_reason", "Vacante en inglés no solicitada" if (is_spanish_only_user and lang == "ENGLISH") else ""),
            role_category=role_cat
        )

    def _heuristic_fallback(
        self,
        job: dict,
        title: str,
        description: str,
        location: str,
        company: str,
        is_spanish_only_user: bool,
        user_location: str = "Ensenada, Baja California"
    ) -> JobTriageResult:
        from src.scrapers.filters import is_disallowed_non_software_role, detect_job_modality, detect_text_language, requires_advanced_english
        
        is_bad_role = is_disallowed_non_software_role(title, description)
        local_keys = [k.strip().lower() for k in user_location.replace(";", ",").split(",") if k.strip()]
        code_mod = detect_job_modality(job, user_local_keywords=local_keys)
        has_adv_eng = requires_advanced_english(f"{title} {description}")
        detected_lang = detect_text_language(description, title).upper()
        
        is_match = (not is_bad_role) and (code_mod in ["remote", "onsite_local"])
        rejection_reason = ""

        if is_bad_role:
            is_match = False
            rejection_reason = "Rol no relacionado con software/TI"
        elif code_mod in ["onsite_relocate", "hybrid"]:
            is_match = False
            rejection_reason = f"Requiere trabajo presencial/híbrido en otra ciudad ({location})"
        elif is_spanish_only_user and (detected_lang == "ENGLISH" or has_adv_eng):
            is_match = False
            rejection_reason = "Vacante en inglés o requiere inglés avanzado C1"

        real_mod_map = {
            "remote": "REMOTE",
            "onsite_local": "ONSITE_LOCAL",
            "hybrid": "HYBRID",
            "onsite_relocate": "ONSITE_RELOCATE",
            "unknown": "UNKNOWN"
        }

        known = ["React", "TypeScript", "Node.js", "Python", "C#", ".NET", "Vue.js", "Angular", "SQL", "PostgreSQL", "Docker", "AWS", "Git"]
        found_skills = [s for s in known if s.lower() in f"{title} {description}".lower()]

        return JobTriageResult(
            is_software_role=not is_bad_role,
            real_modality=real_mod_map.get(code_mod, "UNKNOWN"),
            workplace_location=location if location else ("100% Remoto (Home Office)" if code_mod == "remote" else "México"),
            company_name=company if company and company != "Empresa México" else "Empresa Confidencial (Software)",
            detected_language=detected_lang,
            is_match_for_user=is_match,
            match_percentage=88 if is_match else 40,
            matched_skills=found_skills if found_skills else ["Desarrollo de Software"],
            missing_skills=[],
            summary_highlight=f"Oportunidad técnica detectada en modalidad {code_mod}.",
            rejection_reason=rejection_reason,
            role_category="Full Stack"
        )
