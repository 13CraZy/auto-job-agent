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
    Modelo estructurado del resultado de evaluacion de triaje por IA con deteccion de modalidad y ubicacion real.
    Structured data model for AI job triage evaluation result including modality and workplace location.
    """
    is_software_role: bool = Field(
        description="True si es desarrollo/ingenieria de software o soporte TI de software. False si es ventas, docencia, etc."
    )
    real_modality: Literal["REMOTE", "HYBRID", "ONSITE_LOCAL", "ONSITE_RELOCATE", "UNKNOWN"] = Field(
        default="REMOTE",
        description="Modalidad real: REMOTE (100% Home Office), HYBRID (Presencial y Remoto), ONSITE_LOCAL (En Baja California), ONSITE_RELOCATE (Presencial fuera de BC)"
    )
    workplace_location: str = Field(
        default="100% Remoto (Home Office)",
        description="Ubicacion real donde se desempeña el trabajo (ej: '100% Remoto (Home Office Nacional / LATAM)' o 'Tijuana, Baja California')"
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
    rejection_reason: str = Field(
        default="",
        description="Explicacion breve en espanol si es rechazado"
    )
    role_category: Literal["Backend", "Frontend", "Full Stack", "Soporte Técnico", "Mobile", "DevOps/QA", "Otro"] = Field(
        default="Full Stack",
        description="Categoria tecnica principal del puesto"
    )

class AITriageAgent:
    """
    Agente de Triaje con IA con sistema de Failover Multiproveedor (Groq -> Gemini -> OpenRouter).
    AI Job Triage Agent with multi-provider failover chain.
    """

    def __init__(self):
        # 1. Proveedor Groq (Llama-3.3-70B / Llama-3.1-8B) / Groq Provider
        self.groq_client = None
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_") and not settings.GROQ_API_KEY.startswith("gsk_your_"):
            self.groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )

        # 2. Proveedor Gemini (Google GenAI) / Gemini Provider
        self.gemini_client = None
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") and not settings.GEMINI_API_KEY.startswith("AIzaSy_your_"):
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # 3. Proveedor OpenRouter (Respaldo) / OpenRouter Backup Provider
        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_") and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-your_"):
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AutoJobAgent"
                }
            )

    async def evaluate_job(self, job: Dict[str, Any], user_english_level: str = "Español / Básico") -> JobTriageResult:
        """
        Evalúa una vacante de empleo utilizando LLM, clasifica su modalidad, ubicación real e idioma de los requisitos.
        Evaluates a job posting with LLM, classifies exact modality, workplace location, and core language.
        """
        title = job.get("title", "")
        company = job.get("company", "")
        description = job.get("description", "")[:3000]
        location = job.get("location", "")
        source = job.get("source", "Web")
        job_modality_hint = job.get("modality", "")

        is_spanish_only_user = "español" in user_english_level.lower() or "espanol" in user_english_level.lower() or "básico" in user_english_level.lower() or "basico" in user_english_level.lower()

        prompt = f"""Eres un Evaluador y Reclutador Técnico Senior de Software.
Tu objetivo es analizar esta vacante y extraer con total precisión:
1. Si es desarrollo/ingeniería de software.
2. La MODALIDAD REAL de trabajo (100% Remoto vs Híbrido vs Presencial).
3. La UBICACIÓN REAL del puesto (distinguiendo entre la sede de la empresa y el lugar de trabajo).
4. El IDIOMA PRINCIPAL en el que están redactados los REQUISITOS Y RESPONSABILIDADES (SPANISH o ENGLISH).

OFERTA A EVALUAR:
- Título: {title}
- Empresa (cruda): {company}
- Ubicación indicada en portal: {location}
- Fuente: {source}
- Pista de modalidad: {job_modality_hint}
- Descripción del Puesto:
{description}

PREFERENCIA DEL CANDIDATO:
- Idioma solicitado: {"SOLO OFERTAS CON REQUISITOS EN ESPAÑOL (Descartar ofertas redactadas en inglés)" if is_spanish_only_user else "Acepta ofertas en español e inglés"}
- Residencia: Baja California, México.

REGLAS DE CLASIFICACIÓN ESTRICTAS:
1. IDIOMA DE LA VACANTE (detected_language):
   - "ENGLISH": Si los requisitos técnicos, responsabilidades o cuerpo principal están redactados en inglés (ej: "We are looking for...", "Requirements:", "Responsibilities:", "Qualifications:", "Years of experience"). 
     *IMPORTANTE:* Si el 90% de los requisitos está en inglés, clasifícala como "ENGLISH", AUNQUE al final haya un pie de página o texto legal en español ("Empresa incluyente en México...").
   - "SPANISH": Si los requisitos y responsabilidades están redactados en español (ej: "Buscamos desarrollador...", "Requisitos:", "Ofrecemos prestaciones de ley").

2. MODALIDAD REAL (real_modality):
   - "REMOTE": Es 100% Home Office / Remoto (desde casa en cualquier parte de México o LATAM). Nota: Si la empresa tiene sede en CDMX o Guadalajara pero el esquema de trabajo es 100% Home Office, la modalidad es "REMOTE" y workplace_location es "100% Remoto (Home Office Nacional / LATAM)".
   - "HYBRID": Dice "Presencial y remoto", "esquema mixto", o requiere ir ciertos días a oficina (ej: 2 días presencial, 3 home office).
   - "ONSITE_LOCAL": El trabajo requiere asistencia física en BAJA CALIFORNIA (Ensenada, Tijuana, Mexicali, Tecate, Rosarito).
   - "ONSITE_RELOCATE": El trabajo es presencial fuera de Baja California (ej: requiere vivir o asistir a oficinas en CDMX, Guadalajara, Monterrey, Querétaro, etc.).

3. COMPATIBILIDAD CON EL USUARIO (is_match_for_user):
   - Pasa (true) SOLO SI:
     a) Es de Desarrollo/Software (is_software_role = true)
     b) Es 100% Remoto ("REMOTE") O Presencial en Baja California ("ONSITE_LOCAL").
     {"c) detected_language es 'SPANISH' y NO exige inglés avanzado C1/C2 (Rechazar si detected_language es 'ENGLISH')." if is_spanish_only_user else "c) No exige inglés nativo C2 inaccesible."}
   - Si no cumple cualquiera de los anteriores -> is_match_for_user = false.

4. NOMBRE DE LA EMPRESA (company_name):
   - Limpia estrellas o números de calificación (ej: quita '4.3', '★', 'evaluaciones').
   - Si no hay nombre claro, pon 'Empresa Confidencial (Software)'.

Devuelve ÚNICAMENTE un JSON válido con esta estructura:
{{
  "is_software_role": true,
  "real_modality": "REMOTE",
  "workplace_location": "100% Remoto (Home Office Nacional)",
  "company_name": "Nombre limpio de la empresa",
  "detected_language": "SPANISH",
  "is_match_for_user": true,
  "rejection_reason": "",
  "role_category": "Full Stack"
}}"""

        loop = asyncio.get_event_loop()

        # 1. Intentar con Groq / Try Groq
        if self.groq_client:
            for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                try:
                    def _call_groq():
                        response = self.groq_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "Eres un evaluador de vacantes que responde exclusivamente en JSON estructurado."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.1,
                            response_format={"type": "json_object"}
                        )
                        return response.choices[0].message.content

                    raw_text = await loop.run_in_executor(None, _call_groq)
                    data = json.loads(raw_text.strip())
                    
                    real_mod = data.get("real_modality", "REMOTE").upper()
                    if real_mod not in ["REMOTE", "HYBRID", "ONSITE_LOCAL", "ONSITE_RELOCATE", "UNKNOWN"]:
                        real_mod = "REMOTE" if "remot" in str(data.get("real_modality", "")).lower() else "UNKNOWN"

                    lang = data.get("detected_language", "SPANISH").upper()
                    if lang not in ["SPANISH", "ENGLISH"]:
                        lang = "SPANISH"

                    is_match = bool(data.get("is_match_for_user", True))
                    if is_spanish_only_user and lang == "ENGLISH":
                        is_match = False

                    return JobTriageResult(
                        is_software_role=bool(data.get("is_software_role", True)),
                        real_modality=real_mod,
                        workplace_location=data.get("workplace_location", location or "100% Remoto (Home Office)"),
                        company_name=data.get("company_name", company),
                        detected_language=lang,
                        is_match_for_user=is_match,
                        rejection_reason=data.get("rejection_reason", "Vacante en inglés no solicitada" if (is_spanish_only_user and lang == "ENGLISH") else ""),
                        role_category=data.get("role_category", "Full Stack")
                    )
                except Exception:
                    continue

        # 2. Intentar con OpenRouter / Try OpenRouter
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
                
                real_mod = data.get("real_modality", "REMOTE").upper()
                if real_mod not in ["REMOTE", "HYBRID", "ONSITE_LOCAL", "ONSITE_RELOCATE", "UNKNOWN"]:
                    real_mod = "REMOTE" if "remot" in str(data.get("real_modality", "")).lower() else "UNKNOWN"

                lang = data.get("detected_language", "SPANISH").upper()
                if lang not in ["SPANISH", "ENGLISH"]:
                    lang = "SPANISH"

                is_match = bool(data.get("is_match_for_user", True))
                if is_spanish_only_user and lang == "ENGLISH":
                    is_match = False

                return JobTriageResult(
                    is_software_role=bool(data.get("is_software_role", True)),
                    real_modality=real_mod,
                    workplace_location=data.get("workplace_location", location or "100% Remoto (Home Office)"),
                    company_name=data.get("company_name", company),
                    detected_language=lang,
                    is_match_for_user=is_match,
                    rejection_reason=data.get("rejection_reason", "Vacante en inglés no solicitada" if (is_spanish_only_user and lang == "ENGLISH") else ""),
                    role_category=data.get("role_category", "Full Stack")
                )
            except Exception:
                pass

        # 3. Fallback Heuristico Robusto / Robust Heuristic Fallback
        from src.scrapers.filters import is_disallowed_non_software_role, detect_job_modality, is_spanish_description, requires_advanced_english
        is_bad_role = is_disallowed_non_software_role(title, description)
        code_mod = detect_job_modality(job)
        has_adv_eng = requires_advanced_english(f"{title} {description}")
        is_es = is_spanish_description(description)
        
        is_match = (not is_bad_role) and (code_mod in ["remote", "onsite_local"])
        if is_spanish_only_user:
            if not is_es or has_adv_eng:
                is_match = False

        real_mod_map = {
            "remote": "REMOTE",
            "onsite_local": "ONSITE_LOCAL",
            "hybrid": "HYBRID",
            "onsite_relocate": "ONSITE_RELOCATE",
            "unknown": "UNKNOWN"
        }

        return JobTriageResult(
            is_software_role=not is_bad_role,
            real_modality=real_mod_map.get(code_mod, "UNKNOWN"),
            workplace_location=location if location else ("100% Remoto (Home Office)" if code_mod == "remote" else "México"),
            company_name=company if company and company != "Empresa México" else "Empresa Confidencial (Software)",
            detected_language="SPANISH" if is_es else "ENGLISH",
            is_match_for_user=is_match,
            rejection_reason="Descartado por filtro de idioma (en inglés)" if (is_spanish_only_user and not is_es) else ("Descartado por modalidad o rol" if not is_match else ""),
            role_category="Full Stack"
        )
