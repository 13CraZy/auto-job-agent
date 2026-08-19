import httpx
import asyncio
from typing import Dict, Any, Tuple
from config.settings import settings
from src.scrapers.filters import detect_job_modality

class TelegramNotifier:
    """
    Notificador para Telegram con tarjetas ejecutivas detalladas de vacantes y enlaces directos de postulacion.
    Telegram Notifier with detailed executive job cards and direct application links.
    """

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and not self.bot_token.startswith("your_"))

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Envia un mensaje de prueba a Telegram para verificar que las credenciales son correctas.
        Sends a test message to Telegram to verify credentials.
        """
        if not self.is_configured():
            return False, "Faltan credenciales de Telegram (BOT_TOKEN o CHAT_ID no configurados)."

        test_msg = (
            "🤖 *[Auto Job Hunter AI]*\n\n"
            "✅ *¡Conexión Exitosa con Telegram!*\n"
            "Tu bot está listo para enviarte alertas de empleo personalizadas."
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": test_msg,
                    "parse_mode": "Markdown"
                })
                data = resp.json()
                if data.get("ok"):
                    return True, "Mensaje de prueba enviado exitosamente a tu Telegram."
                else:
                    return False, f"Telegram API Error: {data.get('description', 'Error desconocido')}"
            except Exception as e:
                return False, f"Error conectando a Telegram: {e}"

    async def send_job_alert(
        self,
        job_posting: Dict[str, Any],
        index: int = 1,
        total: int = 1
    ) -> bool:
        """
        Envia una tarjeta ejecutiva de la vacante con formato detallado, modalidad especifica y enlace de postulacion.
        Sends an executive job card with detailed format, specific modality, and application link.
        """
        if not self.is_configured():
            return False

        company = job_posting.get("company", "Empresa Confidencial")
        title = job_posting.get("title", "Puesto")
        source = job_posting.get("source", "Web")
        salary = job_posting.get("salary", "")
        url = job_posting.get("url", "")
        description = job_posting.get("description", "")
        
        # Ubicacion real del puesto vs sede de empresa
        workplace_location = job_posting.get("workplace_location") or job_posting.get("location", "México")
        real_modality = job_posting.get("real_modality", "")
        lang = job_posting.get("detected_language", "SPANISH")
        lang_badge = "Español" if lang == "SPANISH" else "Inglés Técnico"

        # Determinar etiqueta de modalidad clara
        if real_modality == "REMOTE" or "remot" in workplace_location.lower() or "desde casa" in workplace_location.lower():
            modality_badge = "100% REMOTO (Home Office)"
        elif real_modality == "ONSITE_LOCAL" or "baja california" in workplace_location.lower() or "tijuana" in workplace_location.lower() or "ensenada" in workplace_location.lower() or "mexicali" in workplace_location.lower():
            modality_badge = "PRESENCIAL EN BAJA CALIFORNIA"
        elif real_modality == "HYBRID":
            modality_badge = "HÍBRIDO (Presencial y Remoto)"
        else:
            code_mod = detect_job_modality(job_posting)
            if code_mod == "onsite_local":
                modality_badge = "PRESENCIAL EN BAJA CALIFORNIA"
            else:
                modality_badge = "100% REMOTO (Home Office)"

        # Resumen limpio de descripcion
        clean_desc = description.replace("\n", " ").strip()
        if len(clean_desc) > 300:
            clean_desc = clean_desc[:300] + "..."

        salary_text = salary if salary else "A convenir / No publicado"

        markdown_message = f"""🎯 *VACANTE RECOMENDADA [{index}/{total}]*

💼 *Puesto:* {title}
🏢 *Empresa:* {company}
📍 *Lugar de Trabajo:* {workplace_location}
🏠 *Modalidad:* `{modality_badge}`
💰 *Salario:* `{salary_text}`
🌐 *Bolsa de Empleo:* `{source.upper()}`
🗣️ *Idioma de la Oferta:* `{lang_badge}`

📖 *Extracto de Requisitos:*
_{clean_desc}_

🔗 [👉 POSTULARME A ESTA VACANTE EN {source.upper()}]({url})
"""

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                msg_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                resp = await client.post(msg_url, json={
                    "chat_id": self.chat_id,
                    "text": markdown_message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                })
                return resp.status_code == 200
            except Exception as e:
                print(f"[TelegramNotifier] Error enviando alerta: {e}")
                return False

    async def send_final_summary(
        self,
        total_found: int,
        search_terms: list,
        hours_window: float
    ):
        """
        Envia un resumen al finalizar la busqueda multicanal.
        Sends an executive summary upon completing search.
        """
        if not self.is_configured():
            return

        terms_str = ", ".join(search_terms[:4]) if search_terms else "Desarrollo de Software"
        summary_text = f"""🏁 *BÚSQUEDA MULTICANAL COMPLETADA*

📊 *Estadísticas de Búsqueda:*
• Vacantes seleccionadas y entregadas: `{total_found}`
• Criterio: `100% Remoto o Presencial en Baja California`
• Ventana de tiempo: `Últimas {int(hours_window)} horas`
• Roles evaluados: `{terms_str}`

✨ _Todas las ofertas fueron verificadas con IA para confirmar su modalidad real y descartar falsos remotos._"""

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                msg_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                await client.post(msg_url, json={
                    "chat_id": self.chat_id,
                    "text": summary_text,
                    "parse_mode": "Markdown"
                })
            except Exception as e:
                print(f"[TelegramNotifier] Error enviando resumen final: {e}")
