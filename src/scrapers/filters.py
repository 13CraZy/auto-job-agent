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
    # SEO / Marketing Digital / Web Traffic
    r"posicionamiento\s+org[aá]nico", r"tr[aá]fico\s+web", r"especialista\s+seo", r"seo\s+specialist",
    r"marketing\s+digital", r"community\s+manager", r"growth\s+hacker",
    # Hardware / Fibra Optica / Physical Networking
    r"fibra\s+[oó]ptica", r"t[eé]cnico\s+de\s+fibra", r"cableado\s+estructurado", r"instalador\s+de\s+redes",
    r"t[eé]cnico\s+de\s+campo", r"instalador\s+cctv", r"mantenimiento\s+f[ií]sico",
    # Reclutamiento / Recursos Humanos / HR
    r"reclutador", r"reclutadora", r"recursos\s+humanos", r"talent\s+acquisition", r"auxiliar\s+de\s+rh",
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

def detect_text_language(text: str) -> Literal["spanish", "english"]:
    """
    Evalúa y detecta con alta precisión estadística si la descripción principal de la vacante 
    está redactada en español o inglés, analizando la densidad de palabras de requisitos y responsabilidades.
    Evaluates with high statistical precision whether the core job description is in Spanish or English.
    """
    if not text:
        return "spanish"
        
    text_lower = text.lower()
    
    # 1. Indicadores estructurales pesados de vacante en inglés (secciones de la oferta)
    english_structural_indicators = [
        r"\brequirements\b", r"\bresponsibilities\b", r"\bqualifications\b",
        r"\babout\s+(the\s+)?(role|job|company|us)\b", r"\bwhat\s+you('ll|\s+will)\s+do\b",
        r"\bwho\s+you\s+are\b", r"\bwe('re|\s+are)\s+looking\s+for\b", r"\bmust\s+have\b",
        r"\bnice\s+to\s+have\b", r"\byears\s+of\s+experience\b", r"\bkey\s+qualifications\b",
        r"\bwhat\s+we\s+offer\b", r"\bapply\s+now\b", r"\bjob\s+summary\b"
    ]
    en_structural_matches = sum(1 for p in english_structural_indicators if re.search(p, text_lower))

    # Indicadores estructurales pesados de vacante en español
    spanish_structural_indicators = [
        r"\brequisitos\b", r"\bresponsabilidades\b", r"\bconocimientos\b",
        r"\bfunciones\b", r"\bofrecemos\b", r"\bprestaciones\b", r"\bbuscamos\b",
        r"\bperfil\s+del\s+puesto\b", r"\baños\s+de\s+experiencia\b", r"\bactividades\b",
        r"\bque\s+ofrecemos\b", r"\bpost[uú]late\b", r"\bzona\s+de\s+trabajo\b"
    ]
    es_structural_matches = sum(1 for p in spanish_structural_indicators if re.search(p, text_lower))

    # Si hay 2 o más secciones estructurales en inglés y ninguna o 1 en español -> Es claramente en inglés
    if en_structural_matches >= 2 and es_structural_matches == 0:
        return "english"

    # 2. Conteo de frecuencia real de palabras gramaticales (densidad de texto)
    en_tokens = re.findall(r'\b(the|and|with|for|that|this|will|from|your|their|our|you|are|have|working|looking|building|team|is|an|in|on|to|as|by|we|which|who|experience|skills)\b', text_lower)
    es_tokens = re.findall(r'\b(el|la|los|las|un|una|de|en|y|con|para|por|sobre|como|pero|nuestro|nuestra|estamos|trabajando|desarrollo|años|requisitos|conocimientos|ofrecemos|prestaciones|sueldo|salario|puesto|vacante)\b', text_lower)

    en_freq = len(en_tokens) + (en_structural_matches * 5)
    es_freq = len(es_tokens) + (es_structural_matches * 5)

    # 3. Analizar los primeros 800 caracteres (donde comienza la oferta) con mayor peso
    header_sample = text_lower[:800]
    en_header_tokens = len(re.findall(r'\b(the|and|with|for|you|we|are|is|looking|experience|role|skills)\b', header_sample))
    es_header_tokens = len(re.findall(r'\b(el|la|los|las|de|en|y|con|para|buscamos|experiencia|puesto|desarrollo)\b', header_sample))

    total_en_score = en_freq + (en_header_tokens * 2)
    total_es_score = es_freq + (es_header_tokens * 2)

    if total_en_score > total_es_score:
        return "english"
    else:
        return "spanish"

def is_spanish_description(description: str) -> bool:
    """
    Determina si la descripción de la vacante está redactada en idioma español.
    Determines if the job description is written in Spanish.
    """
    return detect_text_language(description) == "spanish"

def is_english_description(description: str) -> bool:
    """
    Determina si la descripción de la vacante está redactada en idioma inglés.
    Determines if the job description is written in English.
    """
    return detect_text_language(description) == "english"


def is_foreign_country_job(job: Dict[str, Any]) -> bool:
    """
    Detecta si una vacante es presencial/local en otro pais de Sudamerica o Europa
    (ej: Argentina, Chile, Colombia, Peru, Espana) y no es para candidatos en Mexico.
    Detects if a job posting is locally based in another South American / European country.
    """
    url = str(job.get("url", "")).lower()
    location = str(job.get("location", "")).lower()
    
    # 1. Chequeo de subdominio de pais en URL / Country subdomain check
    if any(prefix in url for prefix in DISALLOWED_FOREIGN_URL_PREFIXES):
        return True
        
    # 2. Chequeo de pais en la ubicacion / Country name in location string
    is_foreign_loc = any(country in location for country in DISALLOWED_FOREIGN_COUNTRIES)
    if is_foreign_loc:
        if "mexico" in location or "méxico" in location:
            return False
        return True
        
    return False


def is_disallowed_non_software_role(title: str, text: str = "") -> bool:
    """
    Detecta si el puesto es de ventas, docencia, SEO, fibra optica o RH (0ms, 100% preciso).
    Detects if the role is non-technical (sales, teaching, SEO, hardware field tech, HR).
    """
    title_lower = title.lower()
    for p in DISALLOWED_ROLES_PATTERNS:
        if re.search(p, title_lower):
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


def requires_advanced_english(text: str) -> bool:
    """
    Determina si la vacante exige nivel de ingles avanzado o bilingue mandatorio.
    Determines if the job strictly requires advanced/fluent English.
    """
    text_lower = text.lower()
    for pattern in ADVANCED_ENGLISH_PATTERNS:
        if re.search(pattern, text_lower):
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
    Determina la modalidad exacta y ubicacion del empleo:
    - remote: 100% Remoto (Home Office)
    - hybrid: Hibrido / Presencial y remoto
    - onsite_local: Presencial o Hibrido en Baja California (o ciudad configurada)
    - onsite_relocate: Presencial en otra ciudad
    - unknown: No especificado claramente
    
    Determines exact job modality and location category.
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    location = job.get("location", "").lower()
    modality_field = str(job.get("modality", "")).lower()
    full_text = f"{title} {description} {location} {modality_field}"

    # 1. Deteccion de Presencial Local en Baja California / Local city detection
    if not user_local_keywords:
        user_local_keywords = ["ensenada", "tijuana", "mexicali", "tecate", "rosarito", "baja california", "b.c."]
    
    clean_user_keywords = [k.strip().lower() for k in user_local_keywords if len(k.strip()) > 2]
    if any(kw in location for kw in clean_user_keywords) or any(kw in title for kw in clean_user_keywords):
        return "onsite_local"

    # 2. Si el scraper marco explicitamente como remoto (ej. categoria 'desde casa' de Computrabajo o RemoteOK)
    if modality_field == "remote":
        return "remote"

    # 3. Deteccion de Hibrido (Presencial y Remoto) / Hybrid detection
    hybrid_indicators = [
        "presencial y remoto", "hibrido", "híbrido", "hybrid", 
        "días presencial", "dias presencial", "esquema mixto", "esquema híbrido",
        "dias home office", "días home office", "modelo híbrido", "modelo hibrido",
        "trabajo híbrido", "trabajo hibrido"
    ]
    if any(ind in full_text for ind in hybrid_indicators):
        return "hybrid"

    # 4. Descarte de falsos remotos (frases negativas de remoto)
    negative_remote = [
        "no remoto", "no home office", "no se acepta remoto", "esquema presencial", 
        "100% presencial", "presencial en oficina", "asistencia obligatoria a oficina"
    ]
    is_explicit_onsite = any(neg in full_text for neg in negative_remote)
    if is_explicit_onsite and modality_field != "remote":
        return "onsite_relocate"

    # 5. Deteccion de 100% Remoto genuino / 100% Remote detection
    remote_indicators = [
        "100% remoto", "100% remote", "desde casa", "home office permanente", 
        "trabajo 100% remoto", "esquema 100% remoto", "completamente remoto", 
        "trabajo remoto", "remoto", "remote", "teletrabajo"
    ]
    if "remote" in modality_field or "remoto" in modality_field:
        return "remote"
    if "remoto" in location or "remote" in location or "desde casa" in location:
        return "remote"
    if any(ind in full_text for ind in remote_indicators) and not is_explicit_onsite:
        return "remote"

    # 6. Deteccion de Presencial en otras ciudades / Other cities relocation
    disallowed_cities = ["cdmx", "ciudad de méxico", "guadalajara", "monterrey", "querétaro", "puebla", "mérida", "león", "cancún", "oaxaca", "aguascalientes", "san luis potosí", "chihuahua", "toluca"]
    if any(city in location for city in disallowed_cities):
        return "onsite_relocate"

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
