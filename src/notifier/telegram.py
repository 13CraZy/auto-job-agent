import httpx
import asyncio
import html
from typing import Dict, Any, Tuple
from config.settings import settings
from src.scrapers.filters import detect_job_modality

class TelegramNotifier:
    """
    Notificador robusto para Telegram con tarjetas ejecutivas en HTML,
    resistencia total contra caracteres especiales y fallback de entrega.
    """

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and not self.bot_token.startswith("your_"))

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Envia un mensaje de prueba a Telegram para verificar que las credenciales son correctas.
        """
        if not self.is_configured():
            return False, "Faltan credenciales de Telegram (BOT_TOKEN o CHAT_ID no configurados)."

        test_msg = (
            "🤖 <b>[Auto Job Hunter AI - JobJev Engine]</b>\n\n"
            "✅ <b>¡Conexión Exitosa con Telegram!</b>\n"
            "Tu bot está listo para enviarte alertas de empleo verificadas de los últimos 7 días."
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": test_msg,
                    "parse_mode": "HTML"
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
        Envia una tarjeta ejecutiva de la vacante con formato HTML ultra seguro,
        enlace de postulación y fallback garantizado si la API rechaza el marcado.
        """
        if not self.is_configured():
            return False

        company = job_posting.get("company", "Empresa Confidencial")
        title = job_posting.get("title", "Puesto")
        source = job_posting.get("source", "Web")
        salary = job_posting.get("salary", "")
        url = job_posting.get("url", "")
        description = job_posting.get("description", "")
        
        workplace_location = job_posting.get("workplace_location") or job_posting.get("location", "México")
        real_modality = job_posting.get("real_modality", "")
        lang = job_posting.get("detected_language", "SPANISH")
        lang_badge = "🇲🇽 Español" if lang == "SPANISH" else "🇺🇸 Inglés"

        if real_modality == "REMOTE":
            modality_badge = "🏠 100% REMOTO (Home Office)"
        elif real_modality == "ONSITE_LOCAL":
            modality_badge = "🏢 PRESENCIAL LOCAL (Baja California)"
        elif real_modality == "HYBRID":
            modality_badge = "🔀 HÍBRIDO (Presencial y Remoto)"
        else:
            modality_badge = f"📍 {workplace_location}"

        clean_desc = description.replace("\n", " ").strip()
        if len(clean_desc) > 320:
            clean_desc = clean_desc[:320] + "..."

        salary_text = salary if salary else "A convenir / No publicado"
        match_score = job_posting.get("match_percentage", 90)
        matched_skills = job_posting.get("matched_skills", [])
        summary_highlight = job_posting.get("summary_highlight", "")

        skills_text = ", ".join(matched_skills[:5]) if matched_skills else "Desarrollo de Software"
        score_stars = "⭐️" * min(5, max(1, match_score // 20))

        # Escapado seguro para HTML
        e_title = html.escape(title)
        e_company = html.escape(company)
        e_workplace = html.escape(workplace_location)
        e_modality = html.escape(modality_badge)
        e_salary = html.escape(salary_text)
        e_skills = html.escape(skills_text)
        e_source = html.escape(source.upper())
        e_desc = html.escape(clean_desc)
        e_highlight = html.escape(summary_highlight) if summary_highlight else ""

        html_message = (
            f"🎯 <b>VACANTE RECOMENDADA [{index}/{total}]</b>\n"
            f"{score_stars} <b>Compatibilidad:</b> <code>{match_score}%</code>\n\n"
            f"💼 <b>Puesto:</b> {e_title}\n"
            f"🏢 <b>Empresa:</b> {e_company}\n"
            f"📍 <b>Lugar:</b> {e_workplace}\n"
            f"🏠 <b>Modalidad:</b> <code>{e_modality}</code>\n"
            f"💰 <b>Salario:</b> <code>{e_salary}</code>\n"
            f"🛠️ <b>Skills Clave:</b> <code>{e_skills}</code>\n"
            f"🌐 <b>Portal:</b> <code>{e_source}</code>\n"
            f"🗣️ <b>Idioma:</b> {lang_badge}\n"
        )

        if e_highlight:
            html_message += f"\n💡 <b>Análisis JobJev:</b> <i>{e_highlight}</i>\n"

        html_message += (
            f"\n📖 <b>Extracto de Requisitos:</b>\n"
            f"<i>{e_desc}</i>\n\n"
            f"🔗 <a href=\"{url}\">👉 <b>POSTULARME DIRECTO EN {e_source}</b></a>\n"
        )

        msg_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 1. Intento primario con HTML estructurado
                resp = await client.post(msg_url, json={
                    "chat_id": self.chat_id,
                    "text": html_message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                })
                if resp.status_code == 200:
                    return True

                # 2. Fallback de contingencia: texto plano si Telegram rechaza etiquetas
                print(f"  [TelegramNotifier] Advertencia HTML (Status {resp.status_code}): {resp.text}. Reintentando texto plano...")
                plain_message = (
                    f"🎯 VACANTE RECOMENDADA [{index}/{total}]\n"
                    f"Compatibilidad: {match_score}%\n"
                    f"Puesto: {title}\n"
                    f"Empresa: {company}\n"
                    f"Modalidad: {modality_badge}\n"
                    f"Salario: {salary_text}\n"
                    f"Portal: {source.upper()}\n"
                    f"Postulación: {url}\n\n"
                    f"Extracto: {clean_desc}"
                )
                resp_plain = await client.post(msg_url, json={
                    "chat_id": self.chat_id,
                    "text": plain_message,
                    "disable_web_page_preview": False
                })
                return resp_plain.status_code == 200

            except Exception as e:
                print(f"[TelegramNotifier] Error de red enviando alerta: {e}")
                return False

    async def send_final_summary(
        self,
        total_found: int,
        search_terms: list,
        hours_window: float
    ):
        """
        Envia un resumen ejecutivo al finalizar la busqueda multicanal.
        """
        if not self.is_configured():
            return

        terms_str = ", ".join(search_terms[:4]) if search_terms else "Desarrollo de Software"
        days_calc = round(hours_window / 24.0, 1)
        summary_text = (
            f"🏁 <b>BÚSQUEDA JOB HUNTER COMPLETADA</b>\n\n"
            f"📊 <b>Resumen Ejecutivo:</b>\n"
            f"• Vacantes aprobadas y entregadas: <code>{total_found}</code>\n"
            f"• Ventana de tiempo: <code>Últimos {int(days_calc)} días ({int(hours_window)} horas)</code>\n"
            f"• Filtro: <code>100% Remoto o Presencial en Baja California</code>\n"
            f"• Roles rastreados: <code>{html.escape(terms_str)}</code>\n\n"
            f"⚡ <i>Todas las ofertas fueron verificadas y filtradas por el Agente Jev para descartar falsos remotos y no-software.</i>"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                msg_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                await client.post(msg_url, json={
                    "chat_id": self.chat_id,
                    "text": summary_text,
                    "parse_mode": "HTML"
                })
            except Exception as e:
                print(f"[TelegramNotifier] Error enviando resumen final: {e}")
