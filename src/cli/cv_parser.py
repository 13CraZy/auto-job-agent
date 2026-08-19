import os
import re
from pathlib import Path
from typing import Dict, List, Any

class CVParser:
    """Extrae información clave de archivos de CV (PDF, TXT, MD)."""

    TECH_KEYWORDS = [
        "python", "typescript", "javascript", "react", "next.js", "nextjs", "vue", "angular",
        "node", "nodejs", "express", "fastapi", "django", "flask", "c#", ".net", "dotnet",
        "java", "spring", "php", "laravel", "sql", "postgresql", "mysql", "mongodb",
        "redis", "docker", "kubernetes", "aws", "gcp", "azure", "git", "ci/cd",
        "tailwinds", "tailwind", "css", "html", "graphql", "rest api", "linux", "ai",
        "llm", "rag", "langchain", "prompt engineering", "solidity", "web3"
    ]

    ROLE_PATTERNS = {
        "fullstack": ["full stack", "fullstack", "desarrollador full stack", "full stack engineer"],
        "backend": ["backend", "desarrollador backend", "backend developer", "backend engineer"],
        "frontend": ["frontend", "desarrollador frontend", "frontend developer", "frontend engineer"],
        "software_engineer": ["ingeniero de software", "software engineer", "programador", "desarrollador de software"],
        "ai_engineer": ["ai engineer", "ingeniero de ia", "machine learning", "data scientist"],
        "devops": ["devops", "cloud engineer", "sysadmin"]
    }

    def extract_text(self, file_path: str) -> str:
        """Extrae texto plano del archivo proporcionado."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {file_path} no existe.")

        ext = path.suffix.lower()

        if ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
            except Exception as e:
                return f"Error al leer PDF: {str(e)}"

        elif ext in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            raise ValueError(f"Formato de archivo no soportado: {ext}. Usa .pdf, .txt o .md")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Analiza el CV y retorna un diccionario con el perfil extraído."""
        text = self.extract_text(file_path).lower()

        # 1. Extracción de Tecnologías
        found_techs = [tech for tech in self.TECH_KEYWORDS if re.search(r'\b' + re.escape(tech) + r'\b', text)]

        # 2. Roles Recomendados
        suggested_roles = []
        for role, keywords in self.ROLE_PATTERNS.items():
            if any(kw in text for kw in keywords):
                suggested_roles.append(role.replace("_", " ").title())

        if not suggested_roles:
            suggested_roles = ["Desarrollador de Software", "Full Stack Developer"]

        return {
            "file_path": file_path,
            "tech_stack": list(set(found_techs)),
            "suggested_roles": list(set(suggested_roles)),
            "raw_text_length": len(text)
        }
