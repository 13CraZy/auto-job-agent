# Auto Job Hunter & Alert Bot AI (v6.0+ Universal)

> **Buscador Inteligente de Vacantes Multicanal con Inteligencia Artificial**  
> *AI-Powered Multi-Channel Job Hunter & Notification Bot (Telegram, Email & Local Interactive Dashboard)*

---

## 🇪🇸 Descripción en Español

**Auto Job Hunter AI** es un agente automatizado de búsqueda, triaje inteligente y alertas de vacantes de empleo en tiempo real. Rastrea de manera simultánea y en paralelo múltiples bolsas de trabajo (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), utiliza Inteligencia Artificial (**Google Gemini, Groq Llama-3.3 o OpenRouter**) para evaluar la compatibilidad técnica (**Match Score 0-100%**), clasificar la modalidad real (100% Remoto vs Híbrido vs Presencial Local) y envía las mejores oportunidades directamente a tu **Telegram**, **Correo Electrónico** y genera un **Dashboard HTML interactivo local**.

### 🌟 Características Principales:
- ⚡ **Scraping Ultra-Rápido en Paralelo:** Búsqueda simultánea en 6 plataformas en menos de 45 segundos con bloqueo de imágenes/recursos pesados.
- 🧠 **Triaje y Puntuación con IA:** Evalúa cada puesto y calcula su porcentaje de compatibilidad (*Match Score*), habilidades detectadas y resumen ejecutivo.
- 🤖 **Failover Multiproveedor de IA:** Soporte nativo para **Google Gemini 2.5/1.5 Flash**, **Groq (Llama 3.3 70B / 3.1 8B)** y **OpenRouter** con fallback heurístico garantizado.
- ⏱️ **Filtro de Antigüedad Dinámico:** Configura ventanas de 12h, 24h, 36h, 48h o **72h (3 días - Recomendado)** para aplicar siempre a vacantes frescas.
- 📊 **Dashboard HTML Interactivo Local:** Generación automática de reportes visuales con buscador en tiempo real y botones de postulación directa en `vacantes/`.
- 📲 **Alertas Ejecutivas en Telegram:** Tarjetas estructuradas con estrellas de compatibilidad, skills clave y enlaces directos.
- 📧 **Reportes por Correo Electrónico (SMTP):** Envío de un digest HTML moderno y responsivo con botones de postulación directa.
- 🌍 **100% Universal y Personalizable:** Funciona para cualquier perfil técnico, rol, nivel de inglés y ubicación geográfica.

---

## 🇬🇧 English Description

**Auto Job Hunter AI** is an automated, real-time job discovery, AI triage, and multi-channel alerting bot. It concurrently scrapes top job boards (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), applies LLM-powered evaluation (**Google Gemini, Groq Llama-3.3, OpenRouter**) to compute a technical **Compatibility Match Score (0-100%)**, detect exact work modality (100% Remote vs Hybrid vs Local On-site), and delivers curated opportunities straight to your **Telegram**, **Email Inbox**, and generates a local **Interactive HTML Dashboard**.

### 🌟 Key Features:
- ⚡ **Ultra-Fast Parallel Scraping:** Concurrent execution across 6 platforms in under 45 seconds with asset blocking.
- 🧠 **AI Triage & Match Scoring:** Computes technical compatibility (0-100%), extracts core skill matches, and produces executive summaries.
- 🤖 **Multi-Provider AI Failover:** Native support for **Google Gemini**, **Groq**, and **OpenRouter** with guaranteed local fallback.
- ⏱️ **Dynamic Hourly Recency Filtering:** Select 12h, 24h, 36h, 48h, or **72h (3-day recommended)** publication windows.
- 📊 **Local Interactive HTML Dashboard:** Automatic generation of dark-mode responsive reports with live search in `vacantes/`.
- 📲 **Structured Telegram Alert Cards:** Rich cards delivered to your phone with direct application links.
- 📧 **HTML Email Digests:** Modern, responsive email reports via standard SMTP.
- 🌍 **Universal & Open Source:** Adaptable to any candidate role, tech stack, English level, and city/country.

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
Copia el archivo `.env.example` a `.env` y coloca tus claves (puedes usar Groq, Gemini o Telegram):
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
│   ├── user_profile.example.json # Plantilla de perfil tecnico / Sample candidate profile
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
│   │   ├── email_sender.py      # Notificador por correo SMTP / SMTP email notifier
│   │   └── report_generator.py  # Generador de Dashboard HTML y Markdown / Report generator
│   ├── scrapers/
│   │   ├── enricher.py          # Extractor de descripciones completas en tiempo real / Real-time detail enricher
│   │   ├── filters.py           # Filtros de modalidad, idioma y horas / Filters & business logic
│   │   ├── computrabajo.py      # Scraper Computrabajo
│   │   ├── indeed.py            # Scraper Indeed
│   │   ├── linkedin.py          # Scraper LinkedIn
│   │   ├── occ.py               # Scraper OCCMundial
│   │   ├── getonboard.py        # Scraper GetOnBoard
│   │   └── remoteok.py          # Scraper RemoteOK
│   └── orchestrator.py          # Orquestador del pipeline / Pipeline orchestrator
├── templates/                   # Plantillas LaTeX ATS para CV y Cover Letters
├── vacantes/                    # Reportes HTML y Markdown generados
├── main.py                      # Punto de entrada / Entry point
├── requirements.txt             # Dependencias Python / Python dependencies
└── README.md                    # Documentacion / Documentation
```
