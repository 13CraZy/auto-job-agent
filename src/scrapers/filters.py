import re
from datetime import datetime, timedelta
from typing import Dict, Any, Literal, List

# ============================================================
# EXPRESIONES PARA DETECTAR INGLES AVANZADO
# REGEX PATTERNS TO DETECT ADVANCED ENGLISH REQUIREMENTS
# ============================================================
ADVANCED_ENGLISH_PATTERNS = [
    r"fluent\s+english",
    r"advanced\s+english",
    r"english\s+c1",
    r"english\s+c2",
    r"ingl[eé]s\s+avanzado",
    r"ingl[eé]s\s+conversacional",
    r"ingl[eé]s\s+fluido",
    r"ingl[eé]s\s+nativo",
    r"100%\s+fluent",
    r"bilingual\s+\(must\s+have\)",
    r"native\s+english",
    r"nivel\s+de\s+ingl[eé]s:\s*avanzado",
    r"nivel\s+de\s+ingl[eé]s:\s*c1",
]

# ============================================================
# EXPRESIONES PARA DESCARTAR PUESTOS NO DESEADOS (DOCENCIA, VENTAS, SEO, FIBRA OPTICA, RH)
# PATTERNS TO DISCARD NON-SOFTWARE ROLES (TEACHING, SALES, SEO, FIBER OPTICS, HR)
# ============================================================
DISALLOWED_ROLES_PATTERNS = [
    # Docencia / Teaching
    r"profesor", r"profesora", r"docente", r"maestro", r"maestra", r"instructor", r"catedr[aá]tico",
    # Ventas / Sales / Commercial
    r"ejecutivo\s+de\s+ventas", r"ejecutiva\s+de\s+ventas", r"vendedor", r"vendedora",
    r"agente\s+comercial", r"ejecutivo\s+comercial", r"account\s+executive", r"business\s+development",
    r"ejecutivo\s+de\s+cuenta", r"soporte\s+de\s+ventas", r"prospecci[oó]n",
    # SEO / Marketing Digital / Web Traffic / Social Media / Diseño Gráfico Puro
    r"posicionamiento\s+org[aá]nico", r"tr[aá]fico\s+web", r"especialista\s+seo", r"seo\s+specialist",
    r"marketing\s+digital", r"community\s+manager", r"growth\s+hacker", r"social\s+media",
    r"creative\s+designer", r"dise[ñn]ador\s+gr[aá]fico", r"graphic\s+designer",
    r"dise[ñn]ador\s+multimedia", r"content\s+creator", r"creador\s+de\s+contenido",
    # Hardware / Fibra Optica / Physical Networking
    r"fibra\s+[oó]ptica", r"t[eé]cnico\s+de\s+fibra", r"cableado\s+estructurado", r"instalador\s+de\s+redes",
    r"t[eé]cnico\s+de\s+campo", r"instalador\s+cctv", r"mantenimiento\s+f[ií]sico",
    # Reclutamiento / Recursos Humanos / HR
    r"reclutador", r"reclutadora", r"recursos\s+humanos", r"talent\s+acquisition", r"auxiliar\s+de\s+rh",
    # Otras ingenierías no software / Operaciones físicas / Logística
    r"mechanical\s+engineer", r"ingeniero\s+mec[aá]nico", r"ingeniera\s+mec[aá]nica",
    r"civil\s+engineer", r"ingeniero\s+civil", r"ingeniero\s+industrial",
    r"operaci[oó]n\s+de\s+patios", r"jefe\s+de\s+patio", r"jefe\s+de\s+operaci[oó]n",
    r"almacenista", r"montacarguista", r"chofer", r"contador", r"abogado", r"enfermero", r"m[eé]dico"
]

# ============================================================
# PAISES Y CIUDADES FORANEAS A DESCARTAR (FUERA DE MEXICO)
# DISALLOWED FOREIGN LOCATIONS (OUTSIDE MEXICO)
# ============================================================
DISALLOWED_FOREIGN_COUNTRIES = [
    "argentina", "chile", "colombia", "perú", "peru", "venezuela", 
    "uruguay", "paraguay", "bolivia", "ecuador", "españa", "spain",
    "buenos aires", "santiago", "bogotá", "bogota", "lima", "montevideo",
    "córdoba", "cordoba", "medellín", "medellin", "guayaquil", "quito",
    "caracas", "asunción", "asuncion", "la paz", "santa cruz", "valparaíso", "valparaiso"
]

DISALLOWED_FOREIGN_URL_PREFIXES = [
    "https://ar.", "https://cl.", "https://pe.", "https://co.", "https://uy.",
    "https://ve.", "https://ec.", "https://es.", "https://py.", "https://bo."
]

# ============================================================
# VOCABULARIO Y VARIABLES EXTENDIDAS PARA DETECCIÓN DE IDIOMA
# EXTENSIVE DICTIONARY & VARIABLES FOR SPANISH vs ENGLISH DETECTION
# ============================================================

SPANISH_JOB_KEYWORDS = [
    # Términos estructurales de empleo en español
    "experiencia", "requisitos", "conocimientos", "desarrollo", "trabajador", "trabajo", 
    "empresa", "postular", "postúlate", "postulate", "funciones", "ofrecemos", "modalidad", 
    "sueldo", "salario", "habilidades", "licenciatura", "ingeniería", "ingenieria", "años de experiencia", 
    "prestaciones", "beneficios", "prestaciones de ley", "aguinaldo", "vacaciones", "vales de despensa", 
    "seguro de gastos médicos", "sgmm", "jornada laboral", "horario de trabajo", "indispensable", 
    "deseable", "perfil del puesto", "responsabilidades", "buscamos", "solicitamos", "contratación", 
    "tiempo completo", "medio tiempo", "nivel de estudios", "carrera técnica", "zona de trabajo",
    "capacitación", "oportunidad de crecimiento", "ambiente laboral", "bonos", "comisiones",
    "candidato", "candidata", "disponibilidad", "objetivo del puesto", "actividades a realizar",
    "manejo de", "dominio de", "competencias", "formación", "titulado", "pasante", "trunco",
    "home office", "esquema híbrido", "remoto", "presencial", "lunes a viernes"
]

SPANISH_GRAMMAR_STOPWORDS = [
    " de ", " en ", " y ", " con ", " para ", " por ", " los ", " las ", " una ", " uno ", 
    " sobre ", " como ", " pero ", " nuestro ", " nuestra ", " estamos ", " trabajando ", 
    " desarrollo ", " años ", " manejo ", " solución ", " proyectos ", " que ", " del ", " al ",
    " este ", " esta ", " estos ", " estas ", " su ", " sus ", " más ", " mas ", " o ", " entre "
]

ENGLISH_JOB_KEYWORDS = [
    # Structural job keywords in English
    "experience", "requirements", "skills", "responsibilities", "qualifications", "job description", 
    "what you'll do", "what you will do", "who you are", "about the role", "about us", "we are looking for", 
    "benefits", "full-time", "part-time", "years of experience", "must have", "nice to have", "bachelor's", 
    "degree", "salary range", "apply now", "hiring", "key duties", "stack", "relocation", "remote work",
    "equal opportunity", "health insurance", "paid time off", "pto", "fast-paced", "hands-on experience",
    "track record", "problem solving", "collaborative environment", "key qualifications", "role overview"
]

ENGLISH_GRAMMAR_STOPWORDS = [
    " the ", " and ", " with ", " for ", " that ", " this ", " will ", " from ", " your ", 
    " their ", " our ", " you ", " are ", " have ", " working ", " looking ", " building ", 
    " team ", " is ", " an ", " in ", " on ", " to ", " as ", " by ", " we ", " which ", " who "
]

def detect_text_language(text: str, title: str = "") -> Literal["spanish", "english"]:
    """
    Evalúa y detecta con alta precisión estadística si la vacante está redactada en español o inglés.
    Evaluates with high statistical precision whether the job is written in Spanish or English.
    """
    combined = f"{title} {text}".lower().strip()
    if not combined:
        return "spanish"

    # 1. Indicadores estructurales inequívocos en inglés
    english_structural_indicators = [
        r"\brequirements\b", r"\bresponsibilities\b", r"\bqualifications\b",
        r"\babout\s+(the\s+)?(role|job|company|us)\b", r"\bwhat\s+you('ll|\s+will)\s+do\b",
        r"\bwho\s+you\s+are\b", r"\bwe('re|\s+are)\s+looking\s+for\b", r"\bmust\s+have\b",
        r"\bnice\s+to\s+have\b", r"\byears\s+of\s+experience\b", r"\bkey\s+qualifications\b",
        r"\bwhat\s+we\s+offer\b", r"\bapply\s+now\b", r"\bjob\s+summary\b", r"\bremote\s+work\b",
        r"\bkey\s+duties\b", r"\bjob\s+overview\b", r"\bteam\s+overview\b", r"\bbenefits\b"
    ]
    en_structural_matches = sum(1 for p in english_structural_indicators if re.search(p, combined))

    # Indicadores estructurales en español
    spanish_structural_indicators = [
        r"\brequisitos\b", r"\bresponsabilidades\b", r"\bconocimientos\b",
        r"\bfunciones\b", r"\bofrecemos\b", r"\bprestaciones\b", r"\bbuscamos\b",
        r"\bperfil\s+del\s+puesto\b", r"\baños\s+de\s+experiencia\b", r"\bactividades\b",
        r"\bque\s+ofrecemos\b", r"\bpost[uú]late\b", r"\bzona\s+de\s+trabajo\b",
        r"\bhabilidades\b", r"\bprestaciones\s+de\s+ley\b"
    ]
    es_structural_matches = sum(1 for p in spanish_structural_indicators if re.search(p, combined))

    if en_structural_matches >= 1 and es_structural_matches == 0:
        return "english"
    if es_structural_matches >= 1 and en_structural_matches == 0:
        return "spanish"

    # 2. Conteo de tokens gramaticales
    en_tokens = len(re.findall(r'\b(the|and|with|for|that|this|will|from|your|their|our|you|are|have|working|looking|building|team|is|an|in|on|to|as|by|we|which|who|experience|skills|engineer|developer|software)\b', combined))
    es_tokens = len(re.findall(r'\b(el|la|los|las|un|una|de|en|y|con|para|por|sobre|como|pero|nuestro|nuestra|estamos|trabajando|desarrollo|años|requisitos|conocimientos|ofrecemos|prestaciones|sueldo|salario|puesto|vacante|desarrollador|ingeniero)\b', combined))

    # 3. Peso al título
    title_lower = title.lower()
    if any(p in title_lower for p in ["remote work", "engineer -", "developer -", "analyst -", "fullstack developer", "backend engineer", "frontend engineer"]):
        en_tokens += 5

    total_en = en_tokens + (en_structural_matches * 6)
    total_es = es_tokens + (es_structural_matches * 6)
    return "english" if total_en > total_es else "spanish"

def requires_advanced_english(text: str, title: str = "") -> bool:
    """
    Detecta si la vacante explícitamente exige inglés avanzado, C1, C2, fluido o bilingüe.
    Detects if the vacancy explicitly requires advanced/fluent English or bilingual proficiency.
    """
    combined = f"{title} {text}".lower()
    patterns = [
        r"ingl[eé]s\s*(?:avanzado|c1|c2|fluido|conversacional|biling[uü]e|100%|nativo)",
        r"nivel\s+de\s+ingl[eé]s:\s*(?:avanzado|c1|c2|biling[uü]e)",
        r"ingl[eé]s\s*:\s*(?:avanzado|c1|c2|biling[uü]e)",
        r"idiomas:\s*ingl[eé]s",
        r"english:\s*(?:advanced|c1|c2|fluent|native|bilingual)",
        r"must\s+be\s+fluent\s+in\s+english",
        r"fluent\s+in\s+english",
        r"fluent\s+english",
        r"english\s+is\s+(?:a\s+must|required)",
        r"advanced\s+english",
        r"100%\s+english",
        r"bilingual\s+english",
        r"bilingual\s+english/spanish",
        r"bilingual\s+english\s*-\s*spanish"
    ]
    return any(re.search(p, combined) for p in patterns)

def is_spanish_description(description: str, title: str = "") -> bool:
    if requires_advanced_english(description, title):
        return False
    return detect_text_language(description, title) == "spanish"

def is_english_description(description: str, title: str = "") -> bool:
    if requires_advanced_english(description, title):
        return True
    return detect_text_language(description, title) == "english"


def is_foreign_country_job(job_or_location: Any, url_hint: str = "") -> bool:
    """
    Detecta si una vacante es presencial/local en otro pais (ej: Argentina, Chile, Colombia, Peru, Espana)
    y no es para candidatos en Mexico / Remoto LATAM.
    """
    if isinstance(job_or_location, dict):
        url = str(job_or_location.get("url", "")).lower()
        location = str(job_or_location.get("location", "")).lower()
    else:
        location = str(job_or_location).lower()
        url = str(url_hint).lower()
    
    # 1. Chequeo de subdominio de pais en URL
    if any(prefix in url for prefix in DISALLOWED_FOREIGN_URL_PREFIXES):
        return True
        
    # 2. Chequeo de pais en la ubicacion
    is_foreign_loc = any(country in location for country in DISALLOWED_FOREIGN_COUNTRIES)
    if is_foreign_loc:
        if "mexico" in location or "méxico" in location or "remoto" in location or "remote" in location:
            return False
        return True
        
    return False


def is_disallowed_non_software_role(title: str, text: str = "") -> bool:
    """
    Detecta si el puesto es de ventas, docencia, SEO, fibra optica o RH (0ms, 100% preciso).
    Detects if the role is non-technical (sales, teaching, SEO, hardware field tech, HR, graphic design).
    """
    target = f"{title.lower()} {text.lower()[:400]}"
    for p in DISALLOWED_ROLES_PATTERNS:
        if re.search(p, target):
            return True
    return False

# ============================================================
# EXPRESIONES PARA DESCARTAR SOPORTE DE HARDWARE PURO
# PATTERNS TO DISCARD PURE HARDWARE SUPPORT
# ============================================================
DISALLOWED_SUPPORT_PATTERNS = [
    r"mantenimiento\s+de\s+impresoras",
    r"cableado\s+estructurado",
    r"reparaci[oó]n\s+f[ií]sica",
    r"t[eé]cnico\s+de\s+campo",
    r"instalador\s+de\s+c[aá]maras",
    r"mantenimiento\s+preventivo\s+de\s+hardware",
    r"soporte\s+en\s+sitio\s+hardware",
    r"reparaci[oó]n\s+de\s+computadoras",
    r"t[eé]cnico\s+de\s+mantenimiento\s+general",
    r"soporte\s+t[eé]cnico\s+a\s+conmutadores",
    r"telefon[ií]a\s+y\s+redes\s+f[ií]sicas"
]

def passes_technical_support_filter(title: str, description: str) -> bool:
    """
    Valida si una vacante de soporte es tecnica de software (SQL, APIs, Web, Bases de datos)
    y descarta soporte puramente fisico/hardware.
    
    Validates if a support role is software/data/API focused and discards pure physical hardware maintenance.
    """
    full_text = f"{title.lower()} {description.lower()}"
    
    for pattern in DISALLOWED_SUPPORT_PATTERNS:
        if re.search(pattern, full_text):
            return False

    software_indicators = [
        "sql", "api", "software", "web", "aplicaciones", "servidores", 
        "linux", "python", "javascript", "cloud", "aws", "azure", "bugs", 
        "logs", "desarrollo", "base de datos", "database", "crm", "erp"
    ]
    
    is_support_title = "soporte" in title.lower() or "support" in title.lower()
    if is_support_title:
        has_software_focus = any(ind in full_text for ind in software_indicators)
        return has_software_focus
        
    return True


def is_support_role(title: str, text: str = "") -> bool:
    """
    Determina si un puesto es de soporte tecnico de TI/Software.
    Determines if a role is technical IT/Software support.
    """
    title_lower = title.lower()
    if "soporte" in title_lower or "support" in title_lower or "helpdesk" in title_lower or "service desk" in title_lower:
        return True
    return False

def extract_monthly_salary_mxn(text: str) -> float:
    """
    Intenta extraer el salario mensual en MXN del texto o devuelve 0.0 si no se detecta.
    Attempts to extract monthly salary in MXN from text, returning 0.0 if not detected.
    """
    text_clean = text.replace(",", "").replace("$", " ")
    
    # Patron 1: Rango ej: 35000 a 45000 / 35000 - 45000
    range_match = re.search(r'(\d{4,6})\s*(?:-|a|al)\s*(\d{4,6})', text_clean, re.IGNORECASE)
    if range_match:
        val1 = float(range_match.group(1))
        val2 = float(range_match.group(2))
        return max(val1, val2)
        
    # Patron 2: Numero aislado ej: 35000 mensuales
    single_match = re.search(r'(?:sueldo|salario|mensual|neto|bruto)?\s*(\d{4,6})\s*(?:mensual|netos|brutos|mxn|\/mes)?', text_clean, re.IGNORECASE)
    if single_match:
        val = float(single_match.group(1))
        if 5000 <= val <= 300000:
            return val
            
    return 0.0


def detect_job_modality(job: Dict[str, Any], user_local_keywords: List[str] = None) -> Literal["remote", "hybrid", "onsite_local", "onsite_relocate", "unknown"]:
    """
    Determina la modalidad exacta del empleo de forma estricta (Zero-False-Positive):
    - remote: 100% Remoto genuino (Home Office nacional / LATAM)
    - hybrid: Híbrido (requiere asistir días a oficina física)
    - onsite_local: Presencial o Híbrido en Baja California (ciudad local del candidato)
    - onsite_relocate: Presencial o Híbrido en otra ciudad foránea (CDMX, GDL, MTY, etc.)
    - unknown: No determinado
    """
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()
    location = str(job.get("location", "")).lower()
    modality_field = str(job.get("modality", "")).lower()
    full_text = f"{title} {description} {location} {modality_field}"

    # 1. Chequeo de Presencial Local en Baja California / Local city check
    if not user_local_keywords:
        user_local_keywords = ["ensenada", "tijuana", "mexicali", "tecate", "rosarito", "baja california", "b.c."]
    clean_user_keywords = [k.strip().lower() for k in user_local_keywords if len(k.strip()) > 2]

    is_local_city = any(kw in location for kw in clean_user_keywords) or any(kw in title for kw in clean_user_keywords)

    # 2. Detección de Híbrido (Presencial + Remoto)
    hybrid_indicators = [
        "presencial y remoto", "hibrido", "híbrido", "hybrid", 
        "días presencial", "dias presencial", "esquema mixto", "esquema híbrido",
        "dias home office", "días home office", "modelo híbrido", "modelo hibrido",
        "trabajo híbrido", "trabajo hibrido", "2 días en oficina", "3 días en oficina",
        "días en oficina", "guardia presencial", "asistencia a oficina", "ir a oficina"
    ]
    is_hybrid = any(ind in full_text for ind in hybrid_indicators)

    # 3. Detección de ciudades foráneas fuera de Baja California
    other_cities = [
        "cdmx", "ciudad de méxico", "ciudad de mexico", "alvaro obregon", "álvaro obregón", 
        "miguel hidalgo", "cuauhtemoc", "cuauhtémoc", "tlalpan", "benito juarez", "benito juárez", 
        "azcapotzalco", "santa fe", "polanco", "insurgentes", "zapopan", "guadalajara", 
        "monterrey", "san pedro", "querétaro", "queretaro", "puebla", "mérida", "merida", 
        "león", "leon", "cancún", "cancun", "veracruz", "jalisco", "nuevo león", "nuevo leon", 
        "estado de méxico", "estado de mexico", "edomex", "naucalpan", "tlalnepantla", "atizapan", 
        "atizapán", "toluca", "chihuahua", "sonora", "hermosillo", "sinaloa", "culiacan", "aguascalientes"
    ]
    is_in_other_city = any(city in location for city in other_cities)

    # 4. Indicadores de 100% Remoto explícito e indiscutible
    strict_remote_indicators = [
        "100% remoto", "100% remote", "100% home office", "totalmente remoto", 
        "completamente remoto", "full remote", "desde cualquier parte de méxico", 
        "desde cualquier parte de mexico", "desde casa permanente", "home office permanente",
        "esquema 100% home office", "modalidad 100% remota"
    ]
    has_strict_remote_clause = any(ind in full_text for ind in strict_remote_indicators) or modality_field == "remote"

    # Si es híbrido:
    if is_hybrid:
        return "onsite_local" if is_local_city else "onsite_relocate"

    # Si está ubicado físicamente en Ensenada / Tijuana / Baja California:
    if is_local_city:
        if has_strict_remote_clause and "presencial" not in full_text:
            return "remote"
        return "onsite_local"

    # Si está ubicado en otra ciudad (CDMX, Monterrey, Guadalajara, etc.):
    if is_in_other_city:
        # SOLO es remoto si explícitamente dice 100% remoto / desde casa y NO menciona asistencia presencial
        if has_strict_remote_clause and not any(p in full_text for p in ["presencial", "en oficina", "asistir", "híbrido", "hibrido"]):
            return "remote"
        else:
            return "onsite_relocate"

    # Si dice Remoto / Desde casa genérico y no está en otra ciudad específica:
    if has_strict_remote_clause or "remoto" in location or "remote" in location or "desde casa" in location:
        return "remote"

    return "unknown"


def is_within_hours(posted_at: Any, max_hours: float = 48.0) -> bool:
    """
    Verifica si la oferta se publico dentro del limite de horas especificado.
    Checks if job was posted within the specified maximum hours cutoff.
    """
    if not posted_at:
        return True
    if isinstance(posted_at, datetime):
        cutoff = datetime.now() - timedelta(hours=max_hours)
        if posted_at.tzinfo is not None:
            posted_at = posted_at.replace(tzinfo=None)
        return posted_at >= cutoff
    return True

def is_within_days(posted_at: Any, max_days: int = 3) -> bool:
    """
    Compatibilidad hacia atras para limite en dias.
    Backward compatibility check for days limit.
    """
    return is_within_hours(posted_at, max_hours=float(max_days * 24))


def should_include_job(
    job: Dict[str, Any],
    max_hours: float = 48.0,
    modality_pref: str = "Remoto y Presencial en mi Ciudad",
    user_location: str = "Ensenada, Tijuana, Baja California",
    min_salary_relocate: float = 30000.0,
    english_level: str = "Español / Básico"
) -> bool:
    """
    Filtro maestro post-scraping con reglas estrictas:
    1. Debe ser puesto tecnico de desarrollo de software (descarta ventas, docencia, SEO, RH en 0ms).
    2. Descarta vacantes locales presenciales de otros paises (Argentina, Chile, Colombia, Peru, Espana, etc.).
    3. Si exige ingles avanzado/fluido/C1/C2 -> DESCARTA (solo permite espanol o ingles intermedio/tecnico).
    4. Si es en Baja California -> PASA DIRECTO (presencial, hibrido o remoto).
    5. Si es fuera de Baja California -> SOLO PASA SI ES 100% REMOTO PARA MEXICO / LATAM (descarta hibridos y presenciales foraneos).

    Master post-scraping filter enforcing strict user criteria.
    """
    # 0. Filtro estricto de antiguedad por horas / Strict hourly recency check
    posted_at = job.get("posted_at")
    if not is_within_hours(posted_at, max_hours=max_hours):
        return False

    title = job.get("title", "")
    description = job.get("description", "")
    full_text = f"{title}\n{description}"

    # 0.5. Descarta puestos no deseados en 0ms / Discards non-software roles in 0ms
    if is_disallowed_non_software_role(title, full_text):
        return False

    # 1. Descarta soporte hardware puro / Discards pure hardware support
    if not passes_technical_support_filter(title, full_text):
        return False

    # 2. Descarta vacantes presenciales de otros paises / Discards foreign countries local jobs
    if is_foreign_country_job(job):
        return False

    # 3. Filtro de Nivel de Ingles: Descarta si exige ingles avanzado conversacional / Discard advanced english
    has_advanced_english = requires_advanced_english(full_text)
    if has_advanced_english:
        return False

    # 4. Modalidad y ubicacion / Modality and location checks
    local_keywords = [k.strip() for k in user_location.replace(";", ",").split(",") if k.strip()]
    modality = detect_job_modality(job, user_local_keywords=local_keywords)

    # Si es local en Baja California -> PASA DIRECTO / Local BC passes
    if modality == "onsite_local":
        return True

    # Si es fuera de Baja California: SOLO pasa si es 100% REMOTO / Outside BC MUST be 100% remote
    if modality == "remote":
        return True

    # Si es hibrido fuera de Baja California ("presencial y remoto") o presencial foraneo -> DESCARTA
    if modality in ["hybrid", "onsite_relocate", "unknown"]:
        return False

    return False
