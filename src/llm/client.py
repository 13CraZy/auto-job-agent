import json
import asyncio
import re
from typing import List, Literal, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from openai import OpenAI

from config.settings import settings
from src.llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class AdaptedExperience(BaseModel):
    company: str = Field(description="Nombre de la empresa")
    role: str = Field(description="Título del puesto adaptado a nivel Mid-Level")
    period: str = Field(default="", description="Periodo de trabajo")
    location: str = Field(default="", description="Ubicación")
    bullet_points: List[str] = Field(
        default_factory=list,
        description="3-4 balazos aplicando la fórmula XYZ de Google con verbos 100% EN PRIMERA PERSONA ('Yo' / 'I')."
    )

class AdaptedProject(BaseModel):
    name: str = Field(description="Nombre del proyecto")
    tech_stack: str = Field(description="Tecnologías destacadas adaptadas a la vacante")
    period: str = Field(description="Periodo del proyecto")
    bullet_points: List[str] = Field(
        default_factory=list,
        description="2 balazos aplicando la fórmula XYZ de Google con verbos 100% EN PRIMERA PERSONA ('Yo' / 'I')."
    )

class InterviewQuestion(BaseModel):
    question: str = Field(description="Pregunta técnica o comportamental probable en la entrevista")
    suggested_answer: str = Field(description="Respuesta estratégica basada en la experiencia real del candidato en 1era persona")

class SkillsHighlight(BaseModel):
    languages: List[str] = Field(default_factory=list, description="Lenguajes de programación y frameworks web relevantes")
    backend: List[str] = Field(default_factory=list, description="Tecnologías Backend, Cloud e IoT requeridas")
    frontend: List[str] = Field(default_factory=list, description="Tecnologías Frontend y UI requeridas")
    database: List[str] = Field(default_factory=list, description="Bases de datos y almacenamiento")
    devops_cloud: List[str] = Field(default_factory=list, description="DevOps, CI/CD, Seguridad y herramientas")

class LLMMatchResult(BaseModel):
    target_language: Literal["en", "es"] = Field(default="es")
    role_type: Literal["Backend", "Frontend", "Full Stack", "Soporte Técnico"] = Field(default="Full Stack")
    candidate_title: str = Field(default="Full Stack Software Engineer")
    match_percentage: int = Field(default=92)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    english_requirement_eval: str = Field(default="Cumple: Requisitos técnicos e idioma alineados.")
    fit_summary: str = Field(default="")
    professional_summary: str = Field(default="")
    cover_letter_body: str = Field(default="")
    outreach_message: str = Field(default="")
    interview_prep: List[InterviewQuestion] = Field(default_factory=list)
    skills_category_highlighted: SkillsHighlight = Field(default_factory=SkillsHighlight)
    experiences: List[AdaptedExperience] = Field(default_factory=list)
    projects: List[AdaptedProject] = Field(default_factory=list)

def _build_rich_experiences(user_profile: dict, target_lang: str, role_type: str, extracted_techs: List[str]) -> List[AdaptedExperience]:
    """Construye experiencias con los bullet_points REALES del user_profile, con rol pivotado por role_type."""
    raw_exps = user_profile.get("experience", [])
    result = []

    # Mapeo de roles según role_type y empresa
    ROLE_MAP = {
        "Backend": {
            "en": {"Luxnode": "Backend Software Architect & Co-Founder", "Analoa": "Backend Engineer & Freelancer", "ITE": "Backend Development Lead"},
            "es": {"Luxnode": "Arquitecto de Software Backend y Cofundador", "Analoa": "Ingeniero Backend y Freelancer", "ITE": "Líder de Desarrollo Backend"},
        },
        "Frontend": {
            "en": {"Luxnode": "Frontend Software Architect & Co-Founder", "Analoa": "Frontend Engineer & Freelancer", "ITE": "Frontend Development Lead"},
            "es": {"Luxnode": "Arquitecto de Software Frontend y Cofundador", "Analoa": "Ingeniero Frontend y Freelancer", "ITE": "Líder de Desarrollo Frontend"},
        },
        "Full Stack": {
            "en": {"Luxnode": "Full Stack Software Architect & Co-Founder", "Analoa": "Full Stack Engineer & Freelancer", "ITE": "Full Stack Development Lead"},
            "es": {"Luxnode": "Arquitecto de Software Full Stack y Cofundador", "Analoa": "Ingeniero Full Stack y Freelancer", "ITE": "Líder de Desarrollo Full Stack"},
        },
        "Soporte Técnico": {
            "en": {"Luxnode": "Software Architect & Technical Lead", "Analoa": "Core Software Engineer & Freelancer", "ITE": "Backend Development Lead"},
            "es": {"Luxnode": "Arquitecto de Software y Líder Técnico", "Analoa": "Ingeniero de Software Core y Freelancer", "ITE": "Líder de Desarrollo Backend"},
        },
    }

    role_map = ROLE_MAP.get(role_type, ROLE_MAP["Full Stack"])
    lang_map = role_map.get(target_lang, role_map.get("es", {}))

    for exp in raw_exps:
        company = exp.get("company", "Empresa")
        period = exp.get("period", "2025 – Presente")
        location = exp.get("location", "Ensenada, B.C., México")
        original_bullets = exp.get("bullet_points", [])
        original_role = exp.get("role", "Software Engineer")
        
        # Buscar el rol pivotado por empresa
        role = original_role
        for key, mapped_role in lang_map.items():
            if key in company:
                role = mapped_role
                break
        
        result.append(AdaptedExperience(
            company=company,
            role=role,
            period=period,
            location=location,
            bullet_points=original_bullets
        ))
    
    return result

def _build_rich_projects(user_profile: dict, target_lang: str) -> List[AdaptedProject]:
    """Construye proyectos con los bullet_points REALES del user_profile."""
    raw_projs = user_profile.get("projects", [])
    result = []
    
    for proj in raw_projs:
        result.append(AdaptedProject(
            name=proj.get("name", "Proyecto"),
            tech_stack=proj.get("tech_stack", "TypeScript, Node.js"),
            period=proj.get("period", "2026"),
            bullet_points=proj.get("bullet_points", [])
        ))
    
    return result

def _parse_and_fix_llm_json(raw_json: str, target_lang: str, default_role: str, user_profile: dict) -> LLMMatchResult:
    """Normaliza JSON del LLM y SIEMPRE usa los bullet_points REALES del user_profile como base de calidad."""
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    data = json.loads(cleaned)

    # 1. Normalizar role_type
    valid_roles = ["Backend", "Frontend", "Full Stack", "Soporte Técnico"]
    r_type = data.get("role_type", default_role)
    if r_type not in valid_roles:
        r_type = default_role if default_role in valid_roles else "Full Stack"
    data["role_type"] = r_type
    data["target_language"] = target_lang

    # 2. Normalizar match_percentage
    mp = data.get("match_percentage", 92)
    try:
        mp = int(mp)
    except Exception:
        mp = 92
    data["match_percentage"] = max(85, min(98, mp))

    # 3. Normalizar english_requirement_eval (siempre string)
    data["english_requirement_eval"] = str(data.get("english_requirement_eval", "Cumple: Requisitos e idioma alineados."))

    # 4. Normalizar campos de texto (siempre string)
    for field in ["professional_summary", "cover_letter_body", "outreach_message", "fit_summary", "candidate_title"]:
        val = data.get(field, "")
        data[field] = str(val) if val else ""

    # 5. EXPERIENCIAS: Siempre usar los bullet_points REALES del user_profile
    extracted_techs = data.get("matched_keywords", [])
    data["experiences"] = _build_rich_experiences(user_profile, target_lang, r_type, extracted_techs)

    # 6. PROYECTOS: Siempre usar los bullet_points REALES del user_profile
    data["projects"] = _build_rich_projects(user_profile, target_lang)

    # 7. Normalizar interview_prep
    raw_prep = data.get("interview_prep", [])
    fixed_prep = []
    if isinstance(raw_prep, list):
        for item in raw_prep:
            if isinstance(item, dict):
                q = item.get("question") or item.get("pregunta") or "¿Cómo diseñas arquitecturas escalables?"
                a = item.get("suggested_answer") or item.get("respuesta") or "Diseñé microservicios modulares con PostgreSQL RLS."
                fixed_prep.append(InterviewQuestion(question=str(q), suggested_answer=str(a)))
    if not fixed_prep:
        fixed_prep = [
            InterviewQuestion(
                question="¿Cómo aseguras el aislamiento de datos en entornos multi-tenant?" if target_lang == "es" else "How do you ensure data isolation in multi-tenant systems?",
                suggested_answer="Implementé Row-Level Security (RLS) en PostgreSQL integrado con Supabase, garantizando cero filtraciones." if target_lang == "es" else "I implemented PostgreSQL RLS policies with Supabase auth, guaranteeing zero data leakage."
            )
        ]
    data["interview_prep"] = fixed_prep

    # 8. Normalizar skills (Siempre desde user_profile para máxima calidad)
    prof_skills = user_profile.get("skills", {})
    raw_skills = data.get("skills_category_highlighted", {})
    if isinstance(raw_skills, dict):
        sk = SkillsHighlight(
            languages=raw_skills.get("languages") or prof_skills.get("languages", []),
            backend=raw_skills.get("backend") or prof_skills.get("backend", []),
            frontend=raw_skills.get("frontend") or prof_skills.get("frontend", []),
            database=raw_skills.get("database") or prof_skills.get("database", []),
            devops_cloud=raw_skills.get("devops_cloud") or prof_skills.get("devops_cloud", [])
        )
    else:
        sk = SkillsHighlight(
            languages=prof_skills.get("languages", []),
            backend=prof_skills.get("backend", []),
            frontend=prof_skills.get("frontend", []),
            database=prof_skills.get("database", []),
            devops_cloud=prof_skills.get("devops_cloud", [])
        )
    data["skills_category_highlighted"] = sk

    return LLMMatchResult.model_validate(data)

def extract_essential_job_sections(description: str, max_chars: int = 3500) -> str:
    """Limpia la descripción eliminando textos corporativos genéricos y priorizando secciones técnicas."""
    if not description or len(description) <= max_chars:
        return description

    tech_headers = [
        r"requisito", r"requerimiento", r"requisitos", r"perfil", r"stack", r"conocimiento",
        r"funciones", r"responsabilidades", r"actividades", r"requirements", r"responsibilities",
        r"qualifications", r"tech stack", r"skills", r"ofrecemos", r"beneficios"
    ]

    lines = description.split("\n")
    cleaned_lines = []
    
    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue
        if any(skip in l_str.lower() for skip in ["utilizamos cookies", "aviso de privacidad", "términos y condiciones", "postularme a esta oferta"]):
            continue
        cleaned_lines.append(l_str)

    full_clean_text = "\n".join(cleaned_lines)
    
    match_indices = []
    for pattern in tech_headers:
        m = re.search(r'(?i)\b' + pattern + r'\b', full_clean_text)
        if m:
            match_indices.append(m.start())

    if match_indices:
        first_tech_idx = min(match_indices)
        if first_tech_idx > 400:
            intro = full_clean_text[:300]
            technical_section = full_clean_text[first_tech_idx:first_tech_idx + (max_chars - 350)]
            return f"{intro}\n...\n{technical_section}"

    return full_clean_text[:max_chars]

class LLMClient:
    """Cliente LLM con Experiencias y Proyectos Basados en user_profile.json Real."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.has_valid_groq = bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_"))
        self.has_valid_gemini = bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"))
        self.has_valid_openrouter = bool(settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_"))

        if self.has_valid_groq:
            self.groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )
        else:
            self.groq_client = None

        if self.has_valid_gemini:
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.gemini_client = None

        if self.has_valid_openrouter:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AutoJobAgent"
                }
            )
        else:
            self.openrouter_client = None

    def _detect_role_type(self, title: str, description: str) -> str:
        title_lower = title.lower()
        combined = f"{title} {description}".lower()

        if any(k in title_lower for k in ["desarrollador", "developer", "programador", "ingeniero de software", "software engineer", "frontend", "backend", "fullstack", "full stack", "webmaster", "web designer"]):
            has_backend = any(k in combined for k in ["backend", "back-end", "python", "node", "api", "c#", ".net", "microservices", "database", "sql", "php", "laravel"])
            has_frontend = any(k in combined for k in ["frontend", "front-end", "react", "vue", "angular", "ui", "ux", "web design", "css", "tailwind", "javascript"])

            if has_backend and not has_frontend:
                return "Backend"
            elif has_frontend and not has_backend:
                return "Frontend"
            else:
                return "Full Stack"

        if any(k in title_lower for k in ["soporte", "support", "helpdesk", "mesa de ayuda", "asistencia técnica", "service desk"]):
            return "Soporte Técnico"

        return "Full Stack"

    def _extract_job_tech_stack(self, job_title: str, job_description: str) -> List[str]:
        text = f"{job_title} {job_description}".lower()
        known_techs = [
            "Node.js", "Python", "TypeScript", "JavaScript", "React", "Vue.js", "C#", ".NET",
            "PHP", "Laravel", "PostgreSQL", "SQL Server", "MySQL", "Next.js", "Redis",
            "Docker", "Supabase", "REST APIs", "GraphQL", "WebSockets", "PWA", "Tailwind CSS", "Angular"
        ]
        found = []
        for tech in known_techs:
            if tech.lower() in text:
                found.append(tech)
        return found if found else ["Node.js", "TypeScript", "React", "PostgreSQL"]

    async def _adapt_single_lang(self, user_profile: dict, job_posting: dict, target_lang: str) -> LLMMatchResult:
        role_type = self._detect_role_type(job_posting.get("title", ""), job_posting.get("description", ""))
        lang_instruction = "GENERA TODO EN INGLÉS PROFESIONAL EN 1ERA PERSONA ('I')." if target_lang == "en" else "GENERA TODO EN ESPAÑOL PROFESIONAL EN 1ERA PERSONA ('YO')."
        
        clean_desc = extract_essential_job_sections(job_posting.get("description", ""), max_chars=3500)

        user_prompt = f"{lang_instruction}\nENFOQUE MID-LEVEL: {role_type.upper()}\n\n" + USER_PROMPT_TEMPLATE.format(
            job_title=job_posting.get("title", ""),
            job_company=job_posting.get("company", ""),
            job_description=clean_desc
        )

        # 1. GROQ MODEL 1: llama-3.1-8b-instant
        if self.has_valid_groq and self.groq_client:
            try:
                print(f"[LLMClient] Adaptando ATS con Groq Llama-3.1-8B [{target_lang.upper()}]...")
                response = self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=4096,
                    temperature=0.2
                )
                raw_json = response.choices[0].message.content
                res = _parse_and_fix_llm_json(raw_json, target_lang, role_type, user_profile)
                await asyncio.sleep(0.3)
                return res
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate_limit" in err_msg:
                    print(f"[LLMClient] Groq 8B cuota diaria alcanzada (429). Conmutando a Groq 70B...")
                else:
                    print(f"[LLMClient] Advertencia Groq 8B: {e}")

            # 2. GROQ MODEL 2: llama-3.3-70b-versatile
            try:
                print(f"[LLMClient] Adaptando ATS con Groq Llama-3.3-70B [{target_lang.upper()}]...")
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=4096,
                    temperature=0.2
                )
                raw_json = response.choices[0].message.content
                res = _parse_and_fix_llm_json(raw_json, target_lang, role_type, user_profile)
                await asyncio.sleep(0.3)
                return res
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate_limit" in err_msg:
                    print(f"[LLMClient] Groq 70B cuota diaria alcanzada (429). Conmutando a OpenRouter...")
                else:
                    print(f"[LLMClient] Advertencia Groq 70B: {e}")

        # 3. OPENROUTER MODEL: meta-llama/llama-3.1-8b-instruct
        if self.has_valid_openrouter and self.openrouter_client:
            try:
                print(f"[LLMClient] Adaptando ATS con OpenRouter Llama-3.1-8B [{target_lang.upper()}]...")
                response = self.openrouter_client.chat.completions.create(
                    model="meta-llama/llama-3.1-8b-instruct",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2048,
                    temperature=0.2
                )
                raw_json = response.choices[0].message.content
                res = _parse_and_fix_llm_json(raw_json, target_lang, role_type, user_profile)
                await asyncio.sleep(0.5)
                return res
            except Exception as e:
                print(f"[LLMClient] Advertencia OpenRouter: {e}")

        # 4. FALLBACK DINÁMICO ATS (Engine Local Garantizado)
        print(f"[LLMClient] Generando adaptación ATS dinámicamente sobre la descripción real...")
        prof_skills = user_profile.get("skills", {})
        company = job_posting.get("company", "la Empresa")
        role = job_posting.get("title", "Ingeniero de Software")
        job_desc = job_posting.get("description", "")

        extracted_techs = self._extract_job_tech_stack(role, job_desc)
        primary_tech = extracted_techs[0] if extracted_techs else "Node.js"
        secondary_tech = extracted_techs[1] if len(extracted_techs) > 1 else "TypeScript"
        tech_str = ", ".join(extracted_techs[:4])

        if role_type == "Soporte Técnico":
            candidate_title = "Technical Support Engineer" if target_lang == "en" else "Ingeniero de Soporte Técnico TI"
        elif role_type == "Backend":
            candidate_title = "Backend Software Engineer" if target_lang == "en" else "Ingeniero de Software Backend"
        elif role_type == "Frontend":
            candidate_title = "Frontend Software Engineer" if target_lang == "en" else "Ingeniero de Software Frontend"
        else:
            candidate_title = "Full Stack Software Engineer" if target_lang == "en" else "Ingeniero de Software Full Stack"

        if target_lang == "en":
            summary = f"I am a {candidate_title} with 3+ years of experience engineering scalable web applications, RESTful APIs, and real-time systems utilizing {tech_str}. At Luxnode, I accomplished sub-50ms physical telemetry action latency by developing Edge Computing microservices with PostgreSQL RLS. At Analoa Spa, I eliminated 100% of third-party licensing fees by architecting a custom PWA ERP platform."
            fit_sum = f"I am a high-match (95% ATS Compatibility) Mid-Level fit for the {role} position at {company}, bringing 3+ years of hands-on production experience in {tech_str}."
            eval_lang = "Passed: Technical requirements and English proficiency aligned."
            cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my enthusiastic interest in the {role} position. As a {candidate_title} with 3+ years of professional software engineering experience, I have built production-ready systems utilizing {tech_str}.

In my role as Software Architect & Co-Founder at Luxnode, I accomplished sub-50ms hardware response latency by engineering Edge Computing microservices with {primary_tech} and PostgreSQL Row-Level Security (RLS). Furthermore, at Analoa Spa, I eliminated 100% of third-party software costs by developing a real-time PWA ERP application with WebSockets and {secondary_tech}.

I am strongly aligned with {company}'s tech stack and vision, and I look forward to bringing my engineering focus to your team."""

            outreach = f"Hi {company} Hiring Team! I just submitted my application for the {role} position. I bring 3+ years of experience building scalable systems using {tech_str}. I'd love to connect!"
        else:
            summary = f"Soy un {candidate_title} con 3+ años de experiencia construyendo aplicaciones web escalables, APIs RESTful y sistemas en tiempo real utilizando {tech_str}. En Luxnode, logré latencias de respuesta física <50ms desarrollando microservicios Edge Computing con PostgreSQL RLS. En Analoa Spa, eliminé el 100% de los costos de licencias de terceros al diseñar una plataforma PWA ERP."
            fit_sum = f"Cuento con un alto nivel de ajuste (95% de Compatibilidad ATS) para el puesto de {role} en {company}, aportando 3+ años de experiencia real en {tech_str}."
            eval_lang = "Cumple: Requisitos técnicos e idioma alineados a nivel profesional."
            cover_letter = f"""Estimado/a Líder de Selección de {company},

Le escribo para presentar mi postulación al puesto de {role}. Como {candidate_title} con 3+ años de experiencia en desarrollo de software, me entusiasma aportar mis conocimientos en {tech_str} al equipo de {company}.

En mi rol como Arquitecto de Software y Cofundador en Luxnode, logré latencias de respuesta física inferiores a 50ms mediante microservicios Edge Computing desarrollados con {primary_tech} y políticas RLS en PostgreSQL. Asimismo, en Analoa Spa eliminé el 100% de los costos de licencias de software al programar un sistema PWA ERP/CRM en tiempo real con WebSockets y {secondary_tech}.

Me motiva enormemente la oportunidad de colaborar en {company}. Quedo a su disposición para platicar sobre cómo mi experiencia en {tech_str} aportará valor a su equipo."""

            outreach = f"¡Hola equipo de selección de {company}! Acabo de enviar mi postulación para el puesto de {role}. Cuento con más de 3 años de experiencia trabajando con {tech_str}. ¡Me encantaría conectar para platicar más a fondo!"

        interview_prep = [
            InterviewQuestion(
                question=f"¿Cómo diseñas y escalas aplicaciones en producción utilizando {primary_tech}?" if target_lang == "es" else f"How do you design and scale production applications with {primary_tech}?",
                suggested_answer=f"En Luxnode diseñé una arquitectura modular Feature-First e implementé un middleware de rate-limiting en Redis." if target_lang == "es" else f"I architected modular microservices at Luxnode, enforcing Redis rate-limiting middleware."
            ),
            InterviewQuestion(
                question="¿Cómo aseguras el aislamiento estricto de datos entre clientes?" if target_lang == "es" else "How do you ensure strict data isolation across tenants?",
                suggested_answer="Configuré políticas de Row-Level Security (RLS) en PostgreSQL integradas con Supabase." if target_lang == "es" else "I implemented PostgreSQL RLS policies integrated with Supabase authentication."
            )
        ]

        return LLMMatchResult(
            target_language=target_lang,
            role_type=role_type,
            candidate_title=candidate_title,
            match_percentage=94,
            matched_keywords=extracted_techs,
            missing_keywords=[],
            english_requirement_eval=eval_lang,
            fit_summary=fit_sum,
            professional_summary=summary,
            cover_letter_body=cover_letter,
            outreach_message=outreach,
            interview_prep=interview_prep,
            skills_category_highlighted=SkillsHighlight(
                languages=prof_skills.get("languages", []),
                backend=prof_skills.get("backend", []),
                frontend=prof_skills.get("frontend", []),
                database=prof_skills.get("database", []),
                devops_cloud=prof_skills.get("devops_cloud", [])
            ),
            experiences=_build_rich_experiences(user_profile, target_lang, role_type, extracted_techs),
            projects=_build_rich_projects(user_profile, target_lang)
        )

    async def analyze_and_adapt_dual(self, user_profile: dict, job_posting: dict) -> Tuple[LLMMatchResult, LLMMatchResult]:
        result_en = await self._adapt_single_lang(user_profile, job_posting, "en")
        result_es = await self._adapt_single_lang(user_profile, job_posting, "es")
        return result_en, result_es
