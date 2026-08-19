import json
import asyncio
from typing import List
from openai import OpenAI
from google import genai
from config.settings import settings

class JobSynonymExpander:
    """Expansor Inteligente de Sinónimos y Variaciones de Puestos de Empleo con IA."""

    def __init__(self):
        self.groq_client = None
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_"):
            self.groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )

        self.gemini_client = None
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"):
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_"):
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AutoJobAgent"
                }
            )

    async def expand_keywords(self, raw_input: str) -> List[str]:
        """Toma los términos ingresados por el usuario y genera una lista estratégica de 6 a 10 sinónimos."""
        if not raw_input or len(raw_input.strip()) < 2:
            return ["Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend", "Software Engineer"]

        # Heurística inicial para fallback inmediato
        base_terms = [t.strip() for t in raw_input.replace(";", ",").split(",") if t.strip()]

        prompt = f"""Eres un Asesor Senior de Reclutamiento Tech y Experto en Búsqueda de Empleo.
El usuario busca trabajo y ha escrito los siguientes roles o tecnologías clave:
"{raw_input}"

TU TAREA:
Genera una lista de 6 a 10 términos de búsqueda y sinónimos directos (tanto en ESPAÑOL como en INGLÉS) que usan los reclutadores en bolsas de trabajo como LinkedIn, Computrabajo, Indeed y GetOnBoard.

REGLAS:
1. Incluye combinaciones comunes (ejemplo: si busca 'Backend', incluye 'Desarrollador Backend', 'Backend Developer', 'Ingeniero de Software Backend', 'Backend Node.js', etc.).
2. Deben ser términos cortos y directos para usar en un buscador (2 a 4 palabras por término).
3. Devuelve EXCLUSIVAMENTE un JSON válido con la clave 'keywords' como un array de strings.

Ejemplo de formato:
{{
  "keywords": [
    "Desarrollador Full Stack",
    "Full Stack Developer",
    "Desarrollador Backend",
    "Backend Engineer",
    "Software Engineer"
  ]
}}"""

        loop = asyncio.get_event_loop()

        # 1. Intentar con Groq
        if self.groq_client:
            for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                try:
                    def _call_groq():
                        res = self.groq_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "Responde exclusivamente en JSON válido."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.2,
                            response_format={"type": "json_object"}
                        )
                        return res.choices[0].message.content
                    
                    raw_json = await loop.run_in_executor(None, _call_groq)
                    data = json.loads(raw_json.strip())
                    if "keywords" in data and isinstance(data["keywords"], list) and len(data["keywords"]) > 0:
                        return data["keywords"][:10]
                except Exception:
                    continue

        # 2. Intentar con OpenRouter
        if self.openrouter_client:
            try:
                def _call_openrouter():
                    res = self.openrouter_client.chat.completions.create(
                        model="meta-llama/llama-3.1-8b-instruct",
                        messages=[
                            {"role": "system", "content": "Responde exclusivamente en JSON válido."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.2
                    )
                    return res.choices[0].message.content

                raw_json = await loop.run_in_executor(None, _call_openrouter)
                cleaned = raw_json.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(cleaned)
                if "keywords" in data and isinstance(data["keywords"], list) and len(data["keywords"]) > 0:
                    return data["keywords"][:10]
            except Exception:
                pass

        # 3. Fallback Heurístico Robusto si no hay conexión a IA
        expanded = []
        for term in base_terms:
            expanded.append(term)
            if "full" in term.lower() or "stack" in term.lower():
                expanded.extend(["Desarrollador Full Stack", "Full Stack Developer", "Fullstack Engineer"])
            elif "back" in term.lower():
                expanded.extend(["Desarrollador Backend", "Backend Developer", "Ingeniero Backend"])
            elif "front" in term.lower() or "react" in term.lower():
                expanded.extend(["Desarrollador Frontend", "Frontend Developer", "React Developer"])
            elif "software" in term.lower() or "programador" in term.lower() or "dev" in term.lower():
                expanded.extend(["Software Engineer", "Ingeniero de Software", "Desarrollador Web"])

        # Deduplicar preservando orden
        seen = set()
        result = []
        for kw in expanded:
            kw_clean = kw.strip()
            if kw_clean.lower() not in seen and len(kw_clean) > 2:
                seen.add(kw_clean.lower())
                result.append(kw_clean)

        return result[:8] if result else base_terms
