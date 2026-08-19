# Auto Job Hunter & Alert Bot AI (v6.0 Universal)

> **Buscador Inteligente de Vacantes Multicanal con Inteligencia Artificial**  
> *AI-Powered Multi-Channel Job Hunter & Notification Bot (Telegram & Email)*

---

## 🇪🇸 Descripción en Español

**Auto Job Hunter AI** es un agente automatizado de búsqueda y triaje de vacantes de empleo en tiempo real. Rastrea de manera simultánea y en paralelo múltiples bolsas de trabajo (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), utiliza Inteligencia Artificial para filtrar ofertas no técnicas (ventas, docencia, spam) y envía las mejores oportunidades directamente a tu **Telegram** y/o **Correo Electrónico** con enlaces directos para postularte en un solo clic.

### Características Principales:
- ⚡ **Scraping Ultra-Rápido en Paralelo:** Búsqueda simultánea en 6 plataformas en menos de 45 segundos con bloqueo de imágenes/recursos pesados.
- 🧠 **Expansión Inteligente de Sinónimos con IA:** Escribe un término (ej. *Backend Python*) y la IA genera automáticamente 8-10 variantes estratégicas bilingües.
- ⏱️ **Filtro de Antigüedad por Horas:** Configura ventanas de 12h, 24h, 36h, 48h o 72h para aplicar siempre a vacantes recientes.
- 📲 **Alertas a Telegram:** Tarjetas de vacante ejecutivas enviadas a tu bot personal.
- 📧 **Reportes por Correo Electrónico (SMTP):** Envío de un digest HTML moderno y responsivo con botones de postulación directa.
- 🖥️ **Asistente Interactivo por Consola:** Menú visual con `rich`, pruebas de conexión en vivo y asistentes paso a paso.

---

## 🇬🇧 English Description

**Auto Job Hunter AI** is an automated, real-time job discovery and triage bot. It concurrently scrapes top job boards (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), applies AI-powered evaluation to discard non-technical positions (sales, teaching, spam), and sends the curated opportunities straight to your **Telegram** and/or **Email Inbox** with 1-click application links.

### Key Features:
- ⚡ **Ultra-Fast Parallel Scraping:** Concurrent execution across 6 platforms in under 45 seconds with asset blocking.
- 🧠 **AI-Powered Keyword & Synonym Expansion:** Input your target roles and let the LLM generate strategic multi-language search terms.
- ⏱️ **Hourly Recency Filtering:** Select 12h, 24h, 36h, 48h, or 72h publication windows.
- 📲 **Telegram Notifications:** Structured job alert cards delivered to your phone.
- 📧 **HTML Email Digests:** Modern, responsive email reports via standard SMTP.
- 🖥️ **Interactive Terminal Wizard:** Beautiful CLI interface powered by `rich` with live connection tests.

---

## 🚀 Instalación y Uso / Installation & Usage

### 1. Clonar el repositorio / Clone repository:
```bash
git clone https://github.com/tu-usuario/auto-job-agent.git
cd auto-job-agent
```

### 2. Instalar dependencias / Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar `.env` / Configure `.env`:
Copia el archivo `.env.example` a `.env` y coloca tus claves:
```bash
cp .env.example .env
```

### 4. Ejecutar el asistente interactivo / Run the interactive wizard:
```bash
python main.py
```

---

## 📁 Estructura del Proyecto / Project Structure

```text
auto-job-agent/
├── config/
│   ├── settings.py              # Configuracion global / Global settings
│   └── processed_jobs.json      # Base de datos de historial / Seen jobs database
├── src/
│   ├── cli/
│   │   └── wizard.py            # Asistente interactivo en consola / CLI wizard
│   ├── llm/
│   │   ├── synonyms.py          # Expansion de sinonimos con IA / AI synonym expansion
│   │   ├── triage.py            # Evaluador inteligente de vacantes / AI job triage
│   │   └── client.py            # Cliente LLM con failover / LLM failover client
│   ├── notifier/
│   │   ├── telegram.py          # Notificador de Telegram / Telegram notifier
│   │   └── email_sender.py      # Notificador por correo SMTP / SMTP email notifier
│   ├── scrapers/
│   │   ├── filters.py           # Filtros de modalidad y horas / Filters & business logic
│   │   ├── computrabajo.py      # Scraper Computrabajo
│   │   ├── indeed.py            # Scraper Indeed
│   │   ├── linkedin.py          # Scraper LinkedIn
│   │   ├── occ.py               # Scraper OCCMundial
│   │   ├── getonboard.py        # Scraper GetOnBoard
│   │   └── remoteok.py          # Scraper RemoteOK
│   └── orchestrator.py          # Orquestador del pipeline / Pipeline orchestrator
├── main.py                      # Punto de entrada / Entry point
├── requirements.txt             # Dependencias Python / Python dependencies
└── README.md                    # Documentacion / Documentation
```
