import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from config.settings import settings
from src.llm.synonyms import JobSynonymExpander
from src.notifier.telegram import TelegramNotifier
from src.notifier.email_sender import EmailNotifier

console = Console()

class CLIWizard:
    """
    Asistente interactivo en consola para configurar y ejecutar Auto Job Hunter AI v6.0.
    Interactive CLI wizard to configure and execute Auto Job Hunter AI v6.0.
    """

    PREFS_FILE = Path(".user_preferences.json")
    ENV_FILE = Path(".env")

    def __init__(self):
        self.expander = JobSynonymExpander()

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto quitando acentos y convirtiendo a minusculas.
        Normalizes text removing accents and converting to lowercase.
        """
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("ñ", "n"), ("ü", "u")
        )
        t = text.lower().strip()
        for a, b in replacements:
            t = t.replace(a, b)
        return t

    def _check_and_setup_ai_keys(self):
        """
        Guia a nuevos usuarios para configurar su API Key de IA si no tienen ninguna activa.
        Guides new users to set up their AI API key if none is configured.
        """
        has_groq = bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_") and not settings.GROQ_API_KEY.startswith("gsk_your_"))
        has_gemini = bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") and not settings.GEMINI_API_KEY.startswith("AIzaSy_your_"))
        has_openrouter = bool(settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_") and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-your_"))

        if not (has_groq or has_gemini or has_openrouter):
            console.print(
                Panel(
                    "[bold yellow]Configuración Inicial de Inteligencia Artificial (IA):[/bold yellow]\n\n"
                    "El bot utiliza IA para generar sinónimos estratégicos y clasificar vacantes con alta precisión.\n"
                    "• [bold green]Opción 1 (Recomendada y 100% Gratis):[/bold green] [bold white]Groq API[/bold white] (Ultra-rápido)\n"
                    "  Obtén tu clave gratis en: [bold cyan]https://console.groq.com/keys[/bold cyan]\n\n"
                    "• [bold green]Opción 2 (Gratis):[/bold green] [bold white]Google Gemini[/bold white]\n"
                    "  Obtén tu clave gratis en: [bold cyan]https://aistudio.google.com/app/apikey[/bold cyan]\n\n"
                    "[dim]Si no ingresas ninguna, el bot funcionará con filtros heurísticos de código.[/dim]",
                    title="Configuración de IA",
                    border_style="yellow"
                )
            )

            if Confirm.ask("¿Deseas ingresar tu clave de IA (Groq o Gemini) ahora?", default=True):
                key_type = Prompt.ask("Proveedor", choices=["Groq", "Gemini", "OpenRouter"], default="Groq")
                api_key = Prompt.ask(f"Ingresa tu {key_type} API Key", password=True)
                if api_key.strip():
                    if key_type == "Groq":
                        self._update_env("GROQ_API_KEY", api_key.strip())
                        settings.GROQ_API_KEY = api_key.strip()
                    elif key_type == "Gemini":
                        self._update_env("GEMINI_API_KEY", api_key.strip())
                        settings.GEMINI_API_KEY = api_key.strip()
                    elif key_type == "OpenRouter":
                        self._update_env("OPENROUTER_API_KEY", api_key.strip())
                        settings.OPENROUTER_API_KEY = api_key.strip()
                    console.print(f"[bold green][OK] Clave de {key_type} guardada exitosamente en .env[/bold green]\n")

    async def run(self) -> Dict[str, Any]:
        """
        Ejecuta el flujo interactivo completo del asistente.
        Executes the complete interactive wizard flow.
        """
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]AUTO JOB HUNTER & ALERTS BOT AI v6.0[/bold cyan]\n"
                "[bold green]Buscador Inteligente Multicanal | Telegram & Email[/bold green]\n"
                "[dim]Encuentra vacantes técnicas recientes y recíbelas en tu celular o correo[/dim]",
                border_style="cyan"
            )
        )

        saved_prefs = self._load_saved_prefs()

        # ------------------------------------------------------------
        # PASO 0: VERIFICACION DE IA
        # STEP 0: AI KEY VERIFICATION
        # ------------------------------------------------------------
        self._check_and_setup_ai_keys()

        # ------------------------------------------------------------
        # PASO 1: PUESTOS Y EXPANSOR DE SINONIMOS CON IA
        # STEP 1: ROLES & AI SYNONYMS EXPANSION
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 1: Puestos y Tecnologías Deseadas / Target Roles & Tech Stack[/bold yellow]")
        default_roles = saved_prefs.get("raw_keywords", "Full Stack Developer, Backend Node.js, Frontend React")
        user_roles_input = Prompt.ask(
            "Ingresa los puestos o tecnologías que buscas (separados por coma)",
            default=default_roles
        )

        with console.status("[bold cyan]Asistente IA generando sinónimos y variaciones de búsqueda...[/bold cyan]"):
            expanded_keywords = await self.expander.expand_keywords(user_roles_input)

        # Mostrar tabla de terminos generados por IA
        kw_table = Table(title="Términos de Búsqueda Optimizados por IA / AI Search Queries", border_style="cyan")
        kw_table.add_column("#", justify="center", style="dim", width=4)
        kw_table.add_column("Término / Variante Estratégica", style="bold white")
        for i, kw in enumerate(expanded_keywords, 1):
            kw_table.add_row(str(i), kw)
        console.print(kw_table)

        if Confirm.ask("¿Deseas usar estos términos generados por la IA?", default=True):
            final_keywords = expanded_keywords
        else:
            custom_input = Prompt.ask("Ingresa tus términos manuales (separados por coma)")
            final_keywords = [k.strip() for k in custom_input.split(",") if k.strip()]

        # ------------------------------------------------------------
        # PASO 2: VENTANA DE TIEMPO (HORAS)
        # STEP 2: TIME WINDOW (HOURS)
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 2: Antigüedad de Publicación / Recency Window[/bold yellow]")
        console.print("  [bold cyan]1.[/bold cyan] Últimas 12 horas")
        console.print("  [bold cyan]2.[/bold cyan] Últimas 24 horas (1 día)")
        console.print("  [bold cyan]3.[/bold cyan] Últimas 36 horas")
        console.print("  [bold cyan]4.[/bold cyan] Últimas 48 horas (2 días)")
        console.print("  [bold cyan]5.[/bold cyan] Últimas 72 horas (3 días - [bold green]Recomendado[/bold green])")
        
        hours_raw = Prompt.ask(
            "Selecciona la opción deseada (1-5 o ingresa el número de horas)",
            default="5"
        )
        
        hours_map = {"1": 12.0, "2": 24.0, "3": 36.0, "4": 48.0, "5": 72.0, "12": 12.0, "24": 24.0, "36": 36.0, "48": 48.0, "72": 72.0}
        max_hours = hours_map.get(hours_raw.strip(), 72.0)

        # ------------------------------------------------------------
        # PASO 3: MODALIDAD, ESTADO Y SALARIO
        # STEP 3: MODALITY, LOCATION & SALARY FILTERS
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 3: Modalidad de Trabajo / Modality[/bold yellow]")
        console.print("  [bold cyan]1.[/bold cyan] Solo Remoto (100% Home Office)")
        console.print("  [bold cyan]2.[/bold cyan] Remoto y Presencial en mi Ciudad/Estado ([bold green]Recomendado[/bold green])")
        console.print("  [bold cyan]3.[/bold cyan] Presencial Foráneo solo si supera salario mínimo")
        console.print("  [bold cyan]4.[/bold cyan] Cualquiera (Remoto, Presencial o Híbrido)")

        mod_raw = Prompt.ask(
            "Selecciona tu modalidad preferida (1-4)",
            default="2"
        )
        
        norm_mod = self._normalize_text(mod_raw)
        if norm_mod in ["1", "remoto", "remote", "solo remoto", "home office"]:
            modality_pref = "Solo Remoto"
        elif norm_mod in ["2", "local", "mi ciudad", "remoto y presencial"]:
            modality_pref = "Remoto y Presencial en mi Ciudad"
        elif norm_mod in ["3", "foraneo", "salario"]:
            modality_pref = "Presencial Foráneo solo si supera salario mínimo"
        else:
            modality_pref = "Cualquiera"

        user_location = saved_prefs.get("user_location", "Ensenada, Tijuana, Baja California")
        if modality_pref != "Solo Remoto":
            user_location = Prompt.ask(
                "Ingresa tu Ciudad y Estado de residencia (separados por coma)",
                default=user_location
            )

        min_salary_relocate = 30000.0
        if "salario" in modality_pref.lower() or "foraneo" in modality_pref.lower() or "presencial" in modality_pref.lower():
            min_salary_str = Prompt.ask(
                "Salario mensual mínimo requerido para vacantes en otras ciudades (MXN)",
                default=str(int(saved_prefs.get("min_salary_relocate", 30000)))
            )
            try:
                min_salary_relocate = float(min_salary_str)
            except ValueError:
                min_salary_relocate = 30000.0

        # ------------------------------------------------------------
        # PASO 4: NIVEL DE IDIOMA / INGLES
        # STEP 4: LANGUAGE & ENGLISH REQUIREMENT LEVEL
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 4: Nivel de Idioma / English Level[/bold yellow]")
        console.print("  [bold cyan]1.[/bold cyan] Español / Básico ([bold green]Descarta vacantes que exijan inglés avanzado C1/C2[/bold green])")
        console.print("  [bold cyan]2.[/bold cyan] Bilingüe / Inglés Avanzado (Acepta ofertas 100% en inglés)")
        console.print("  [bold cyan]3.[/bold cyan] Cualquiera (Muestra todas las vacantes)")

        lang_raw = Prompt.ask(
            "Selecciona tu preferencia de idioma (1-3 o escribe 'espanol' / 'ingles')",
            default="1"
        )
        
        norm_lang = self._normalize_text(lang_raw)
        if norm_lang in ["1", "espanol", "basico", "espanol / basico", "espanol basico", "spanish", "es"]:
            english_level = "Español / Básico"
        elif norm_lang in ["2", "ingles", "bilingue", "avanzado", "english", "en"]:
            english_level = "Bilingüe / Inglés Avanzado"
        else:
            english_level = "Cualquiera"

        # ------------------------------------------------------------
        # PASO 5: PLATAFORMAS DE BUSQUEDA
        # STEP 5: JOB PLATFORMS
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 5: Plataformas de Empleo / Job Boards[/bold yellow]")
        console.print("  [bold cyan]1.[/bold cyan] Todas (Computrabajo, Indeed, LinkedIn, OCC, GetOnBoard, RemoteOK - [bold green]Recomendado[/bold green])")
        console.print("  [bold cyan]2.[/bold cyan] Personalizado (Elegir una por una)")
        
        all_platforms = ["Computrabajo", "Indeed", "LinkedIn", "OCCMundial", "GetOnBoard", "RemoteOK"]
        plat_raw = Prompt.ask("¿Dónde deseas buscar? (1 o 2)", default="1")
        norm_plat = self._normalize_text(plat_raw)

        if norm_plat in ["1", "todas", "all", "t"]:
            selected_platforms = all_platforms
        else:
            selected_platforms = []
            for p in all_platforms:
                if Confirm.ask(f"  • ¿Buscar en {p}?", default=True):
                    selected_platforms.append(p)
            if not selected_platforms:
                selected_platforms = all_platforms

        # ------------------------------------------------------------
        # PASO 6: CANAL DE TELEGRAM
        # STEP 6: TELEGRAM CHANNEL
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 6: Canal de Notificaciones Telegram / Telegram Channel[/bold yellow]")
        enable_telegram = Confirm.ask("¿Deseas recibir las alertas en tu Telegram?", default=saved_prefs.get("enable_telegram", True))
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID

        if enable_telegram:
            if not bot_token or not chat_id or bot_token.startswith("your_"):
                console.print(
                    Panel(
                        "[bold cyan]Instrucciones para conectar tu Telegram en 1 minuto:[/bold cyan]\n"
                        "1. Abre Telegram y busca al bot oficial [bold white]@BotFather[/bold white].\n"
                        "2. Envía el comando [bold yellow]/newbot[/bold yellow], sigue los pasos y copia tu [bold green]HTTP API Token[/bold green].\n"
                        "3. Luego busca al bot [bold white]@userinfobot[/bold white], dale a [bold yellow]Iniciar[/bold yellow] y copia tu [bold green]ID numérico[/bold green].",
                        title="Configuración de Telegram",
                        border_style="yellow"
                    )
                )
                bot_token = Prompt.ask("Ingresa tu TELEGRAM_BOT_TOKEN", password=True)
                chat_id = Prompt.ask("Ingresa tu TELEGRAM_CHAT_ID")
                self._update_env("TELEGRAM_BOT_TOKEN", bot_token)
                self._update_env("TELEGRAM_CHAT_ID", chat_id)
                settings.TELEGRAM_BOT_TOKEN = bot_token
                settings.TELEGRAM_CHAT_ID = chat_id

            # Prueba de conexion en vivo
            tg_notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
            if Confirm.ask("¿Deseas enviar un mensaje de prueba a Telegram ahora?", default=True):
                with console.status("[bold cyan]Enviando mensaje de prueba a Telegram...[/bold cyan]"):
                    ok, msg = await tg_notifier.test_connection()
                if ok:
                    console.print(f"[bold green][OK] {msg}[/bold green]")
                else:
                    console.print(f"[bold red][ERROR] {msg}[/bold red]")

        # ------------------------------------------------------------
        # PASO 7: CANAL DE CORREO ELECTRONICO (SMTP)
        # STEP 7: EMAIL CHANNEL (SMTP)
        # ------------------------------------------------------------
        console.print("\n[bold yellow]PASO 7: Canal de Correo Electrónico (Email / SMTP) / Email Channel[/bold yellow]")
        enable_email = Confirm.ask("¿Deseas recibir un reporte ordenado por Correo Electrónico?", default=saved_prefs.get("enable_email", False))
        
        smtp_user = settings.SMTP_USER
        smtp_pass = settings.SMTP_PASSWORD
        to_email = settings.NOTIFICATION_EMAIL

        if enable_email:
            if not smtp_user or not smtp_pass or not to_email or smtp_user.startswith("tu_correo"):
                console.print(
                    Panel(
                        "[bold cyan]Configuración de Correo Gmail (Gratuito y Seguro):[/bold cyan]\n"
                        "1. Entra a [bold white]https://myaccount.google.com/apppasswords[/bold white]\n"
                        "2. Genera una [bold green]Contraseña de Aplicación[/bold green] de 16 letras.\n"
                        "3. Ingresa tu correo y esa contraseña de 16 letras a continuación.",
                        title="Configuración de Email SMTP",
                        border_style="yellow"
                    )
                )
                smtp_user = Prompt.ask("Ingresa tu Correo Remitente (Gmail/Outlook)")
                smtp_pass = Prompt.ask("Ingresa tu Contraseña de Aplicación (16 letras)", password=True)
                to_email = Prompt.ask("Ingresa el Correo donde deseas RECIBIR las vacantes", default=smtp_user)
                
                self._update_env("SMTP_USER", smtp_user)
                self._update_env("SMTP_PASSWORD", smtp_pass)
                self._update_env("NOTIFICATION_EMAIL", to_email)
                self._update_env("ENABLE_EMAIL", "true")
                settings.SMTP_USER = smtp_user
                settings.SMTP_PASSWORD = smtp_pass
                settings.NOTIFICATION_EMAIL = to_email

            email_notifier = EmailNotifier(
                smtp_user=smtp_user,
                smtp_password=smtp_pass,
                notification_email=to_email
            )
            if Confirm.ask("¿Deseas enviar un correo de prueba ahora?", default=True):
                with console.status("[bold cyan]Conectando con el servidor SMTP y enviando prueba...[/bold cyan]"):
                    ok, msg = email_notifier.test_connection(to_email)
                if ok:
                    console.print(f"[bold green][OK] {msg}[/bold green]")
                else:
                    console.print(f"[bold red][ERROR] {msg}[/bold red]")

        # ------------------------------------------------------------
        # PASO 8: GUARDADO Y RESUMEN
        # STEP 8: SAVE & SUMMARY
        # ------------------------------------------------------------
        config = {
            "raw_keywords": user_roles_input,
            "keywords": final_keywords,
            "max_hours": max_hours,
            "modality_pref": modality_pref,
            "user_location": user_location,
            "min_salary_relocate": min_salary_relocate,
            "english_level": english_level,
            "platforms": selected_platforms,
            "enable_telegram": enable_telegram,
            "enable_email": enable_email,
            "telegram_token": bot_token,
            "telegram_chat_id": chat_id,
            "smtp_user": smtp_user,
            "notification_email": to_email
        }

        self._save_prefs(config)
        self._print_summary(config)
        return config

    def _update_env(self, key: str, value: str):
        """
        Actualiza o agrega una variable en el archivo .env.
        Updates or appends an environment variable in .env.
        """
        lines = []
        if self.ENV_FILE.exists():
            with open(self.ENV_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()

        key_found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f"{key}={value}\n")

        with open(self.ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.environ[key] = value

    def _load_saved_prefs(self) -> Dict[str, Any]:
        """
        Carga las preferencias guardadas desde .user_preferences.json.
        Loads saved preferences from .user_preferences.json.
        """
        if self.PREFS_FILE.exists():
            try:
                with open(self.PREFS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_prefs(self, prefs: Dict[str, Any]):
        """
        Guarda las preferencias del usuario en .user_preferences.json.
        Saves user preferences to .user_preferences.json.
        """
        try:
            with open(self.PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _print_summary(self, config: Dict[str, Any]):
        """
        Muestra una tabla de confirmacion antes de iniciar el scraping.
        Displays confirmation table before initiating search.
        """
        table = Table(title="Resumen de Búsqueda Configurada / Search Summary", border_style="green")
        table.add_column("Parámetro", style="bold cyan")
        table.add_column("Configuración", style="white")

        table.add_row("Puestos y Variantes", ", ".join(config["keywords"][:4]) + f" (+{len(config['keywords'])-4} más)" if len(config["keywords"]) > 4 else ", ".join(config["keywords"]))
        table.add_row("Antigüedad Máxima", f"Últimas {int(config['max_hours'])} horas")
        table.add_row("Modalidad Preferida", config["modality_pref"])
        table.add_row("Ubicación Local", config["user_location"])
        table.add_row("Nivel de Idioma", config["english_level"])
        table.add_row("Plataformas", ", ".join(config["platforms"]))
        table.add_row("Canal Telegram", "Activo" if config["enable_telegram"] else "Inactivo")
        table.add_row("Canal Correo (Email)", f"Activo ({config.get('notification_email')})" if config["enable_email"] else "Inactivo")

        console.print("\n")
        console.print(table)
        console.print("\n[bold green]Iniciando búsqueda de alta velocidad... / Launching search...[/bold green]\n")
