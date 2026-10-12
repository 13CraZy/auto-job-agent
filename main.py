import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
# Load environment variables from .env file
load_dotenv()

from src.cli.wizard import CLIWizard
from src.orchestrator import JobAgentOrchestrator

async def main():
    """
    Punto de entrada principal de la aplicacion.
    Inicia el asistente interactivo en consola y luego ejecuta el orquestador de busqueda.

    Main application entry point.
    Launches the interactive CLI wizard and then runs the job search orchestrator.
    """
    # 1. Modo automatico con preferencias guardadas o asistente interactivo
    # 1. Automatic mode using saved preferences or interactive wizard
    prefs_file = Path(".user_preferences.json")
    if ("--auto" in sys.argv or "-y" in sys.argv or "--yes" in sys.argv) and prefs_file.exists():
        print("[*] Iniciando en modo automatico usando .user_preferences.json...")
        with open(prefs_file, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    else:
        wizard = CLIWizard()
        user_config = await wizard.run()

    # 2. Extraer parametros seleccionados por el usuario
    # 2. Extract user-selected parameters
    keywords = user_config.get("keywords", ["Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend"])
    max_hours = user_config.get("max_hours", 168.0)
    platforms = user_config.get("platforms", None)
    modality_pref = user_config.get("modality_pref", "Cualquiera")
    user_location = user_config.get("user_location", "Ciudad de México, México")
    min_salary_relocate = user_config.get("min_salary_relocate", 30000.0)
    english_level = user_config.get("english_level", "Cualquiera")
    enable_telegram = user_config.get("enable_telegram", True)
    enable_email = user_config.get("enable_email", False)

    # 3. Iniciar el orquestador de busqueda y alertas multicanal
    # 3. Launch the multi-channel job hunter orchestrator
    orchestrator = JobAgentOrchestrator()
    await orchestrator.run(
        keywords=keywords,
        max_hours=max_hours,
        selected_platforms=platforms,
        modality_pref=modality_pref,
        user_location=user_location,
        min_salary_relocate=min_salary_relocate,
        english_level=english_level,
        enable_telegram=enable_telegram,
        enable_email=enable_email
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] Busqueda cancelada por el usuario. / Search cancelled by user.")
        sys.exit(0)
