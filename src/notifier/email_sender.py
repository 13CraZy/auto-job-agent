import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Tuple
from datetime import datetime

from config.settings import settings

class EmailNotifier:
    """Notificador por Correo Electrónico con plantillas HTML modernas y soporte SMTP seguro."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        notification_email: str = None
    ):
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.notification_email = notification_email or settings.NOTIFICATION_EMAIL

    def is_configured(self) -> bool:
        """Verifica si los parámetros básicos de correo están completos."""
        return bool(
            self.smtp_host 
            and self.smtp_user 
            and self.smtp_password 
            and self.notification_email
            and not self.smtp_user.startswith("tu_correo")
        )

    def test_connection(self, recipient: str = None) -> Tuple[bool, str]:
        """Prueba la conexión SMTP enviando un correo de verificación en vivo."""
        to_addr = recipient or self.notification_email
        if not to_addr or not self.smtp_user or not self.smtp_password:
            return False, "Faltan credenciales SMTP (Usuario, Contraseña o Destinatario)."

        subject = "🔔 [Auto Job Hunter] Prueba de Conexión Exitosa"
        html_content = """
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; color: #f8fafc; padding: 30px; border-radius: 12px; border: 1px solid #1e293b;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #38bdf8; margin: 0; font-size: 24px;">🤖 Auto Job Hunter AI</h1>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 5px;">Sistema de Alertas de Empleo Automatizado</p>
            </div>
            <div style="background: #1e293b; padding: 20px; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 20px;">
                <h3 style="color: #10b981; margin: 0 0 10px 0;">✅ ¡Conexión SMTP Establecida con Éxito!</h3>
                <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5; margin: 0;">
                    Este es un correo de prueba para certificar que tu bot de empleo puede enviarte alertas personalizadas directamente a tu bandeja de entrada.
                </p>
            </div>
            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">
                Configurado exitosamente • Auto Job Agent v6.0
            </p>
        </div>
        """

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Auto Job Hunter <{self.smtp_user}>"
            msg["To"] = to_addr

            msg.attach(MIMEText("Prueba de conexión SMTP exitosa para Auto Job Hunter AI.", "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=12.0)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=12.0)
                server.starttls()

            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, [to_addr], msg.as_string())
            server.quit()
            return True, "Correo de prueba enviado correctamente."
        except Exception as e:
            return False, f"Error conectando al servidor SMTP: {e}"

    async def send_jobs_digest(self, jobs: List[Dict[str, Any]], search_title: str = "Resumen de Vacantes") -> bool:
        """Envía un resumen ejecutivo con todas las vacantes encontradas en un formato HTML estilizado."""
        if not self.is_configured() or not jobs:
            return False

        loop = asyncio.get_event_loop()

        def _send():
            to_addr = self.notification_email
            subject = f"🎯 {len(jobs)} Nuevas Vacantes Encontradas — {search_title} [{datetime.now().strftime('%d/%m/%Y')}]"

            # Generar tarjetas HTML para cada vacante
            job_cards_html = ""
            for idx, j in enumerate(jobs, 1):
                title = j.get("title", "Puesto")
                company = j.get("company", "Empresa")
                location = j.get("location", "Ubicación no especificada")
                source = j.get("source", "Web").upper()
                salary = j.get("salary", "")
                url = j.get("url", "#")
                desc = j.get("description", "")
                desc_snippet = desc.replace("\n", " ").strip()[:240] + ("..." if len(desc) > 240 else "")

                salary_badge = f'<span style="background: #14532d; color: #4ade80; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px;">💰 {salary}</span>' if salary else ""

                job_cards_html += f"""
                <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="background: #0369a1; color: #bae6fd; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">{source}</span>
                            {salary_badge}
                            <h3 style="color: #f8fafc; font-size: 18px; margin: 8px 0 4px 0;">{idx}. {title}</h3>
                            <p style="color: #38bdf8; font-size: 14px; font-weight: 500; margin: 0 0 8px 0;">🏢 {company} &nbsp;•&nbsp; 📍 {location}</p>
                        </div>
                    </div>
                    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 14px 0;">
                        {desc_snippet}
                    </p>
                    <div>
                        <a href="{url}" target="_blank" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;">
                            👉 Postularme / Ver Vacante
                        </a>
                    </div>
                </div>
                """

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="margin: 0; padding: 20px; background: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
                <div style="max-width: 680px; margin: 0 auto; background: #0f172a; border-radius: 12px; padding: 24px; border: 1px solid #1e293b;">
                    <div style="border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 20px; text-align: center;">
                        <h1 style="color: #38bdf8; font-size: 22px; margin: 0 0 6px 0;">🤖 Auto Job Hunter AI</h1>
                        <p style="color: #94a3b8; font-size: 14px; margin: 0;">
                            Reporte de <strong>{len(jobs)} vacantes seleccionadas</strong> para tu perfil
                        </p>
                    </div>

                    {job_cards_html}

                    <div style="border-top: 1px solid #334155; padding-top: 16px; margin-top: 24px; text-align: center;">
                        <p style="color: #64748b; font-size: 12px; margin: 0;">
                            Generado automáticamente por Auto Job Agent • Filtro inteligente & cero spam
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Auto Job Hunter <{self.smtp_user}>"
            msg["To"] = to_addr

            plain_text = f"Auto Job Hunter: {len(jobs)} nuevas vacantes encontradas.\n\n"
            for idx, j in enumerate(jobs, 1):
                plain_text += f"{idx}. {j.get('title')} en {j.get('company')} ({j.get('location')})\n   Enlace: {j.get('url')}\n\n"

            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=20.0)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20.0)
                server.starttls()

            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, [to_addr], msg.as_string())
            server.quit()
            return True

        try:
            return await loop.run_in_executor(None, _send)
        except Exception as e:
            print(f"[EmailNotifier] Error enviando correo de vacantes: {e}")
            return False
