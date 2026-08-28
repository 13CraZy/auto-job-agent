import asyncio
import sys
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
    # 1. Ejecutar el asistente interactivo de configuracion
    # 1. Run the interactive configuration wizard
    wizard = CLIWizard()
    user_config = await wizard.run()

    # 2. Extraer parametros seleccionados por el usuario
    # 2. Extract user-selected parameters
    keywords = user_config.get("keywords", ["Desarrollador Full Stack", "Desarrollador Backend", "Desarrollador Frontend"])
    max_hours = user_config.get("max_hours", 72.0)
    platforms = user_config.get("platforms", None)
    modality_pref = user_config.get("modality_pref", "Cualquiera")
    user_location = user_config.get("user_location", "Ensenada, Tijuana, Baja California")
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
