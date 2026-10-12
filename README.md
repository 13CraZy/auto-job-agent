# Auto Job Hunter & Alert Bot AI (v6.0+ Universal)

> **Buscador Inteligente de Vacantes de Software en México y Remoto con Agente Jev & LLMs**  
> *AI-Powered Multi-Channel Job Hunter & Notification Bot (Telegram, Email & Local Interactive Dashboard)*

---

## 🇪🇸 Descripción en Español

**Auto Job Hunter AI** es un agente automatizado de búsqueda, triaje inteligente y alertas de vacantes de desarrollo de software en tiempo real, adaptado para cualquier desarrollador en la República Mexicana o que busque trabajo 100% Remoto nacional / LATAM.

Rastrea de manera simultánea múltiples bolsas de trabajo (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), utiliza el **Motor JobJev** (Arquitectura dual: Heurística local ultrarrápida System 1 en <5ms + escalado System 2 con **Groq Llama-3.3 70B Versatile** o **Google Gemini Flash**) para evaluar la compatibilidad técnica (**Match Score 0-100%**), clasificar la modalidad real (100% Remoto vs Híbrido vs Presencial Local) y envía las oportunidades validadas directamente a tu **Telegram**, **Correo Electrónico** y genera un **Dashboard HTML interactivo local**.

### 🌟 Características Principales:
- ⚡ **Scraping Paralelo Optimizado:** Extracción concurrente en plataformas líderes con bloqueo estricto de assets pesados (imágenes, fuentes, css).
- 🧠 **Motor JobJev (System 1 + System 2):**
  - **System 1 (Local <5ms):** Filtra en 0ms roles de ventas/RH/soporte hardware físico, valida fechas, detecta idiomas y analiza ubicación geográfica con reglas deterministas.
  - **System 2 (LLM Escalado):** Si hay ambigüedad o falta información, consulta modelos de alto rendimiento como Groq Llama 3.3 70B o Gemini 2.5/1.5 Flash sin agotar cuotas.
- ⏱️ **Ventana de Tiempo Ampliada (Hasta 7 Días / 168h):** Encuentra ofertas desde las últimas 12h hasta 7 días completos de publicación.
- 🇲🇽 **Diseñado para Cualquier Usuario en México:**
  - Soporte nativo para cualquier metrópoli o estado: **CDMX, Guadalajara/Zapopan, Monterrey, Tijuana, Querétaro, Puebla, Mérida, etc.**
  - Si buscas "Solo Remoto", descarta automáticamente vacantes híbridas foráneas que exijan asistencia física a oficinas de otra ciudad.
  - Si buscas "Remoto y Presencial en mi Ciudad", admite empleos presenciales o híbridos en tu localidad y sólo 100% remoto para otras ciudades.
- 📲 **Alertas Ejecutivas en Telegram:** Formato HTML seguro, con rate-limiting automático, tarjetas ejecutivas con skills requeridos y enlace directo de postulación.
- 🛡️ **Deduplicación Robusta:** Algoritmo que rastrea parámetros canónicos (`?jk=`, IDs nativos) evitando falsos duplicados en Indeed o CompuTrabajo.
- 🧪 **Suite de Pruebas Automatizadas 100% Aislada:** Verifica todo el pipeline sin enviar alertas a tu Telegram real ni alterar tu historial de vacantes.

---

## 🇬🇧 English Description

**Auto Job Hunter AI** is an automated, real-time job discovery, AI triage, and multi-channel alerting bot designed for software developers in Mexico and LATAM remote candidates.

It concurrently scrapes top job boards (*Computrabajo, Indeed, LinkedIn, OCCMundial, GetOnBoard, RemoteOK*), leverages the **JobJev Dual Engine** (System 1 local heuristics in <5ms + System 2 LLM evaluation via **Groq Llama-3.3 70B** / **Google Gemini**) to compute a technical **Compatibility Match Score (0-100%)**, detect genuine modality (100% Remote vs Hybrid vs Local On-site), and delivers curated opportunities directly to your **Telegram**, **Email Inbox**, and generates a local **Interactive HTML Dashboard**.

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

### 3. Configurar variables de entorno / Configure `.env`:
Copia el archivo `.env.example` a `.env` y configura tus proveedores preferidos:
```bash
cp .env.example .env
```

Variables clave recomendadas:
- `GROQ_API_KEY`: Clave gratuita de [console.groq.com](https://console.groq.com) (modelo Llama-3.3-70b-versatile, ultra veloz).
- `GEMINI_API_KEY`: Clave de [aistudio.google.com](https://aistudio.google.com) (opcional / respaldo).
- `TELEGRAM_BOT_TOKEN`: Token obtenido hablando con `@BotFather` en Telegram.
- `TELEGRAM_CHAT_ID`: Tu Chat ID personal obtenido con `@userinfobot`.
- `MAX_HOURS_OLD`: `168.0` (Para buscar ofertas de los últimos 7 días).

### 4. Ejecutar el asistente interactivo / Run the interactive wizard:
```bash
python main.py
```
El asistente te guiará paso a paso para configurar:
1. Roles y tecnologías deseadas (ej: *Full Stack, Python, React, Backend*).
2. Ventana de tiempo (12h, 24h, 48h, 72h o 7 días).
3. Modalidad y tu ciudad de residencia en México (ej: *Ciudad de México, CDMX*, *Guadalajara, Jalisco*, *Monterrey*, etc.).
4. Nivel de inglés requerido (ej: *Español / Básico* para descartar ofertas que exijan inglés C1 fluido).

### 5. Modo automático (para cron o ejecuciones programadas):
Una vez guardadas tus preferencias en la primera ejecución, puedes ejecutarlo sin preguntas interactivas:
```bash
python main.py --auto
```

---

## 🧪 Ejecutar Suite de Tests / Run Test Suite

El proyecto incluye una suite de pruebas de regresión unitaria y de integración end-to-end (16 tests):

```bash
python -m unittest tests/test_full_suite.py
```

> [!NOTE]
> Los tests se ejecutan de manera **100% aislada**: utilizan mocks para Telegram y una base de datos temporal, por lo que **no enviarán alertas a tu celular ni modificarán tu archivo de vacantes ya procesadas**.

---

## 📁 Estructura del Proyecto / Project Structure

```text
auto-job-agent/
├── config/
│   ├── settings.py               # Configuración global y constantes
│   ├── user_profile.example.json # Plantilla de perfil técnico
│   └── processed_jobs.json       # Historial de vacantes procesadas (deduplicación)
├── src/
│   ├── cli/
│   │   └── wizard.py             # Asistente interactivo en consola Rich
│   ├── jev/
│   │   ├── primitives.py         # Tipos y contratos del motor JobJev
│   │   └── engine.py             # Motor System 1 (Local Heuristics <5ms) + System 2 (LLM)
│   ├── llm/
│   │   ├── synonyms.py           # Expansión de sinónimos técnicos
│   │   ├── triage.py             # Triaje y clasificador de compatibilidad
│   │   └── client.py             # Cliente unificado LLM (Groq, Gemini, OpenRouter)
│   ├── notifier/
│   │   ├── telegram.py           # Notificador Telegram con formato HTML seguro
│   │   ├── email_sender.py       # Notificador por correo SMTP
│   │   └── report_generator.py   # Generador de Dashboard HTML y Markdown en vacantes/
│   ├── scrapers/
│   │   ├── enricher.py           # Extractor de descripciones completas en tiempo real
│   │   ├── filters.py            # Filtros de roles de software, idioma y ciudades de México
│   │   ├── computrabajo.py       # Scraper CompuTrabajo México
│   │   ├── indeed.py             # Scraper Indeed México
│   │   ├── linkedin.py           # Scraper LinkedIn Jobs
│   │   ├── occ.py                # Scraper OCCMundial
│   │   ├── getonboard.py         # Scraper GetOnBoard
│   │   └── remoteok.py           # Scraper RemoteOK
│   └── orchestrator.py           # Orquestador del pipeline completo
├── tests/
│   └── test_full_suite.py        # Suite de pruebas automatizadas
├── vacantes/                     # Dashboards HTML y reportes Markdown generados
├── main.py                       # Punto de entrada de la aplicación
├── requirements.txt              # Dependencias Python
├── .env.example                  # Plantilla de variables de entorno
└── README.md                     # Documentación oficial
```

---

## 📄 Licencia / License

Distribuido bajo la licencia MIT. Libre para uso personal o comercial.
