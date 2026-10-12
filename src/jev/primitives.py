"""
⚡ JEV PRIMITIVES & SYSTEM 1 DECISION CORE
============================================================
Implementación en Python de los tres primitivos de Jev (choice, score, noul)
inspirados en LuxJev (E:\Luxnode), no-autorregresivos, deterministas (<5ms),
con calibración de confianza y protección contra trampas de exclusión.
============================================================
"""

import re
import math
import unicodedata
from typing import List, Dict, Any, Tuple, Optional

# ─── TOKENIZADOR Y NORMALIZACIÓN LÉXICA ───────────────────────────────

COMMON_STOPWORDS = {
    # Español
    "de", "la", "el", "en", "y", "a", "los", "se", "del", "las", "por", "un", "para", "con",
    "no", "una", "su", "al", "lo", "como", "mas", "pero", "sus", "le", "ya", "o", "este",
    "si", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "tambien", "me", "hasta",
    "hay", "donde", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni",
    "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "algunos",
    # English
    "the", "and", "to", "of", "a", "in", "for", "is", "on", "that", "by", "this", "with",
    "i", "you", "it", "not", "or", "be", "are", "from", "at", "as", "your", "all", "have",
    "new", "more", "an", "was", "we", "will", "home", "can", "us", "about", "if", "my"
}

def normalize_text(text: str) -> str:
    """Elimina acentos y normaliza texto a minúsculas limpias."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    clean = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return clean.lower().strip()

def tokenize(text: str) -> List[str]:
    """Tokeniza texto normalizado y descarta palabras vacías irrelevantes."""
    clean = normalize_text(text)
    words = re.findall(r'[a-z0-9+#.-]+', clean)
    return [w for w in words if len(w) >= 2 and w not in COMMON_STOPWORDS]

def get_stem(word: str) -> str:
    """Extrae la raíz léxica aproximada de una palabra (ES / EN)."""
    w = word.lower()
    if len(w) <= 3:
        return w
    # Sufijos en español
    w = re.sub(r'(?:mientos?|ciones?|amente|adoras?|adores?|adora|ador|ancias?|encias?)$', '', w)
    w = re.sub(r'(?:iendo|ando|aron|ieron|aran|ieran|aste|iste|aban|abas|amos)$', '', w)
    w = re.sub(r'(?:aba|ia|io|ar|er|ir|es|en|as|an|os|al|el|il|ol|ul|o|a|e)$', '', w)
    # Sufijos en inglés
    w = re.sub(r'(?:ingly|edly|ments?|tions?|ships?|ness)$', '', w)
    w = re.sub(r'(?:ing|ed|ly)$', '', w)
    w = re.sub(r'(?:er|es|s)$', '', w)
    return w

def calculate_token_similarity(prompt_tokens: List[str], criteria_text: str) -> float:
    """
    Calcula la similitud semántica ponderada entre tokens y un texto criterio:
    - Coincidencia exacta: 2.0 pts
    - Coincidencia de raíz (stem): 1.5 pts
    - Prefijo léxico (>=4 chars): 0.8 pts
    """
    criteria_tokens = tokenize(criteria_text)
    if not criteria_tokens or not prompt_tokens:
        return 0.0

    matches = 0.0
    for ct in criteria_tokens:
        ct_stem = get_stem(ct)
        for pt in prompt_tokens:
            if pt == ct:
                matches += 2.0
            elif len(ct_stem) >= 3 and get_stem(pt) == ct_stem:
                matches += 1.5
            elif len(pt) >= 4 and len(ct) >= 4 and (pt.startswith(ct[:4]) or ct.startswith(pt[:4])):
                matches += 0.8

    score = matches / (len(criteria_tokens) * 2.0)
    return min(1.0, score)

def softmax(scores: List[float], temperature: float = 0.4) -> List[float]:
    """Calcula probabilidades Softmax calibradas con temperatura para distribución de confianza."""
    if not scores:
        return []
    max_s = max(scores)
    temp = max(0.01, temperature)
    exp_scores = [math.exp((s - max_s) / temp) for s in scores]
    sum_exp = sum(exp_scores)
    if sum_exp <= 0:
        return [1.0 / len(scores)] * len(scores)
    return [e / sum_exp for e in exp_scores]


# ─── PRIMITIVOS JEV ───────────────────────────────────────────────────

def choice(
    prompt: str,
    criteria: Dict[str, str],
    default_value: str = "",
    temperature: float = 0.35
) -> Tuple[str, float, Dict[str, float]]:
    """
    ⚡ PRIMITIVO JEV 'choice':
    Evalúa un texto contra múltiples opciones de criterios y retorna:
    (opcion_ganadora, confianza, diccionario_scores_normalizados)
    """
    prompt_tokens = tokenize(prompt)
    labels = list(criteria.keys())
    raw_scores = []

    for label in labels:
        score_val = calculate_token_similarity(prompt_tokens, criteria[label])
        raw_scores.append(score_val)

    if not raw_scores or max(raw_scores) == 0.0:
        fallback = default_value or (labels[0] if labels else "")
        return fallback, 0.0, {k: 0.0 for k in labels}

    probs = softmax(raw_scores, temperature=temperature)
    best_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
    best_label = labels[best_idx]
    best_prob = probs[best_idx]

    # Confianza calibrada: combinación de probabilidad softmax y presencia de similitud pura
    calibrated_confidence = (best_prob * 0.7) + (min(1.0, raw_scores[best_idx]) * 0.3)

    score_dict = {labels[i]: round(probs[i], 3) for i in range(len(labels))}
    return best_label, round(calibrated_confidence, 3), score_dict


def score(
    prompt: str,
    target_skills: List[str],
    weights: Optional[Dict[str, float]] = None
) -> Tuple[int, float, List[str]]:
    """
    ⚡ PRIMITIVO JEV 'score':
    Evalúa cuantitativamente la afinidad técnica de un texto contra una lista de habilidades.
    Retorna: (porcentaje_0_a_100, confianza, lista_habilidades_encontradas)
    """
    clean_prompt = normalize_text(prompt)
    prompt_tokens = tokenize(prompt)
    matched = []
    total_weight = 0.0
    accum_score = 0.0

    for skill in target_skills:
        w = (weights or {}).get(skill, 1.0)
        total_weight += w

        skill_norm = normalize_text(skill)
        # Búsqueda exacta de skill compuesto (ej: "next.js", "node.js", "sql server")
        if re.search(r'\b' + re.escape(skill_norm) + r'\b', clean_prompt):
            matched.append(skill)
            accum_score += w
        else:
            # Similitud token/stem
            sim = calculate_token_similarity(prompt_tokens, skill)
            if sim >= 0.75:
                matched.append(skill)
                accum_score += (w * sim)

    if total_weight <= 0:
        return 75, 0.5, matched

    raw_ratio = accum_score / total_weight
    # Calibración a escala ATS (base 60 + hasta 38 adicionales por matches)
    base_match = 65 if len(matched) >= 2 else (50 if len(matched) == 1 else 30)
    calculated_pct = int(min(98, max(20, base_match + (raw_ratio * 33))))

    confidence = min(1.0, (len(matched) * 0.2) + (raw_ratio * 0.4))
    return calculated_pct, round(confidence, 3), matched


def noul(
    prompt: str,
    forbidden_patterns: List[str],
    threshold_matches: int = 1
) -> Tuple[bool, float, str]:
    """
    ⚡ PRIMITIVO JEV 'noul':
    Comprueba límites de frontera y trampas de exclusión.
    Retorna: (is_triggered, confianza, motivo_de_disparo)
    """
    clean_p = normalize_text(prompt)
    detected_reasons = []

    for pattern in forbidden_patterns:
        if re.search(pattern, clean_p, re.IGNORECASE):
            detected_reasons.append(pattern)

    triggered = len(detected_reasons) >= threshold_matches
    confidence = 0.98 if triggered else 0.95
    reason_str = ", ".join(detected_reasons[:2]) if detected_reasons else ""
    return triggered, confidence, reason_str


# ─── ESCUDO CONTRA TRAMPAS DE EXCLUSIÓN Y NEGACIÓN ────────────────────

MODALITY_REJECTION_TRAPS = [
    r"\bno\s+(?:es\s+)?remoto\b",
    r"\bno\s+home\s*office\b",
    r"\bno\s+aplica\s+(?:trabajo\s+)?(?:a\s+distancia|remoto|home\s*office)\b",
    r"\b100%\s+presencial\b",
    r"\btotalmente\s+presencial\b",
    r"\bpresencial\s+(?:obligatorio|indispensable|estricto)\b",
    r"\basistir\s+(?:a\s+las?\s+)?oficinas?\s+diari(?:o|amente)\b",
    r"\blunes\s+a\s+viernes\s+en\s+oficina\b",
    r"\bradicar\s+indispensable\s+en\b"
]

LANGUAGE_C1_TRAPS = [
    r"\badvanced\s+english\b",
    r"\benglish\s+c1\b",
    r"\benglish\s+c2\b",
    r"\bc[12]\s+(?:level|english|ingles)\b",
    r"\bbilingual\s+c[12]\b",
    r"\bfluent\s+english\b",
    r"\bingles\s+avanzado\b",
    r"\bingles\s+fluido\b",
    r"\bingles\s+c[12]\b",
    r"\bc[12]\s+ingles\b",
    r"\bingles\s+conversacional\s+avanzado\b",
    r"\bbilingual\s+\(must\s+have\)\b",
    r"\bnative\s+english\b",
    r"\b100%\s+fluent\b",
    r"\bnivel\s+de\s+ingles:\s*avanzado\b",
    r"\bnivel\s+de\s+ingles:\s*c1\b",
    r"\bdo\s+not\s+apply\s+without\s+fluent\s+english\b"
]

DISALLOWED_ROLE_TRAPS = [
    r"\b(?:profesor|profesora|docente|maestro|maestra|instructor|catedratico)\b",
    r"\b(?:ejecutivo\s+de\s+ventas|ejecutiv[ao].*ventas?|vendedor|vendedora|agente\s+comercial|telemarketing|call\s*center|atencion\s+a\s+clientes|ventas\b|asesor\s+comercial|prospeccion)\b",
    r"\b(?:posicionamiento\s+organico|trafico\s+web|especialista\s+seo|marketing\s+digital|community\s+manager)\b",
    r"\b(?:disenador\s+grafico|graphic\s+designer|creativo\s+multimedia|creador\s+de\s+contenido)\b",
    r"\b(?:fibra\s+optica|tecnico\s+de\s+fibra|cableado\s+estructurado|instalador\s+de\s+redes|instalador\s+cctv)\b",
    r"\b(?:reclutador|recursos\s+humanos|auxiliar\s+de\s+rh|talent\s+acquisition)\b",
    r"\b(?:almacenista|montacarguista|chofer|repartidor|contador|abogado|enfermero|medico|cajero)\b"
]
