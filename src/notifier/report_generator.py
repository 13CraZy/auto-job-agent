import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class ReportGenerator:
    """
    Generador de reportes locales interactivos en HTML moderno y Markdown para Auto Job Hunter AI.
    Generates modern interactive local HTML and Markdown reports for discovered jobs.
    """

    def __init__(self, output_dir: Path = None):
        from config.settings import settings
        self.output_dir = output_dir or settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_reports(
        self,
        jobs: List[Dict[str, Any]],
        search_keywords: List[str],
        max_hours: float,
        user_location: str
    ) -> tuple[Path, Path]:
        """
        Genera archivo HTML interactivo y Markdown digest con las vacantes encontradas.
        Returns paths to (html_file, md_file).
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"reporte_vacantes_{timestamp_str}.html"
        md_file = self.output_dir / f"reporte_vacantes_{timestamp_str}.md"

        self._generate_html(html_file, jobs, search_keywords, max_hours, user_location)
        self._generate_markdown(md_file, jobs, search_keywords, max_hours, user_location)

        return html_file, md_file

    def _generate_html(
        self,
        target_path: Path,
        jobs: List[Dict[str, Any]],
        keywords: List[str],
        max_hours: float,
        user_location: str
    ):
        kw_badges = " ".join([f'<span class="badge badge-primary">{k}</span>' for k in keywords[:6]])
        
        cards_html = []
        for idx, j in enumerate(jobs, 1):
            title = j.get("title", "Puesto")
            company = j.get("company", "Empresa Confidencial")
            location = j.get("workplace_location") or j.get("location", "México")
            source = j.get("source", "Web")
            url = j.get("url", "#")
            salary = j.get("salary") or "No especificado / A convenir"
            score = j.get("match_percentage", 90)
            skills = j.get("matched_skills", [])
            summary = j.get("summary_highlight", "")
            desc = j.get("description", "").replace("\n", "<br>")
            modality = j.get("real_modality", "REMOTE")
            lang = j.get("detected_language", "SPANISH")

            mod_badge_class = "badge-success" if modality == "REMOTE" else ("badge-info" if modality == "ONSITE_LOCAL" else "badge-warning")
            mod_label = "100% Remoto" if modality == "REMOTE" else ("Presencial Local" if modality == "ONSITE_LOCAL" else "Híbrido")
            
            skills_badges = " ".join([f'<span class="badge badge-skill">{s}</span>' for s in skills[:6]]) if skills else '<span class="badge badge-skill">Software</span>'

            score_color = "#10B981" if score >= 90 else ("#F59E0B" if score >= 75 else "#6366F1")

            card = f"""
            <div class="job-card" data-title="{title.lower()}" data-company="{company.lower()}" data-source="{source.lower()}">
                <div class="card-header">
                    <div>
                        <div class="card-badges">
                            <span class="badge {mod_badge_class}">{mod_label}</span>
                            <span class="badge badge-source">{source}</span>
                            <span class="badge badge-lang">{'🇲🇽 Español' if lang == 'SPANISH' else '🇺🇸 Inglés'}</span>
                        </div>
                        <h2 class="job-title">{title}</h2>
                        <div class="job-company">🏢 {company} &nbsp;•&nbsp; 📍 {location}</div>
                    </div>
                    <div class="score-circle" style="border-color: {score_color}; color: {score_color};">
                        <span class="score-num">{score}%</span>
                        <span class="score-label">MATCH</span>
                    </div>
                </div>

                <div class="card-meta">
                    <div class="meta-item">
                        <span class="meta-icon">💰</span>
                        <span><strong>Salario:</strong> {salary}</span>
                    </div>
                </div>

                <div class="skills-row">
                    {skills_badges}
                </div>

                {f'<div class="ai-highlight">💡 <strong>Análisis IA:</strong> {summary}</div>' if summary else ''}

                <div class="card-actions">
                    <button class="btn btn-outline" onclick="toggleDetails('desc-{idx}')">Ver Requisitos</button>
                    <a href="{url}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">👉 Postularme en {source}</a>
                </div>

                <div id="desc-{idx}" class="job-description-drawer" style="display: none;">
                    <div class="desc-content">{desc}</div>
                </div>
            </div>
            """
            cards_html.append(card)

        all_cards_rendered = "\n".join(cards_html) if cards_html else '<div class="empty-state">No se encontraron vacantes para este criterio.</div>'

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto Job Hunter AI - Reporte Ejecutivo ({len(jobs)} Vacantes)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090D16;
            --surface: #111827;
            --surface-hover: #1F2937;
            --border: #374151;
            --text-main: #F9FAFB;
            --text-muted: #9CA3AF;
            --primary: #3B82F6;
            --primary-glow: rgba(59, 130, 246, 0.25);
            --success: #10B981;
            --warning: #F59E0B;
            --accent: #8B5CF6;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; }}
        body {{ background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 2rem 1rem; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        
        header {{
            background: linear-gradient(180deg, rgba(31, 41, 55, 0.6) 0%, rgba(17, 24, 39, 0.4) 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        .header-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem; }}
        h1 {{ font-size: 1.8rem; font-weight: 800; background: linear-gradient(90deg, #60A5FA, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stats-badge {{ background: var(--surface-hover); border: 1px solid var(--border); padding: 0.5rem 1rem; border-radius: 999px; font-weight: 600; color: var(--success); }}
        
        .header-meta {{ display: flex; flex-wrap: wrap; gap: 1.5rem; color: var(--text-muted); font-size: 0.9rem; margin-top: 1rem; }}
        .header-meta span strong {{ color: var(--text-main); }}

        .search-bar-wrap {{ margin: 1.5rem 0; display: flex; gap: 1rem; }}
        .search-input {{
            flex: 1;
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 0.85rem 1.25rem;
            border-radius: 12px;
            color: #fff;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .search-input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-glow); }}

        .badge {{ display: inline-block; padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge-primary {{ background: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-success {{ background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-info {{ background: rgba(139, 92, 246, 0.2); color: #C084FC; border: 1px solid rgba(139, 92, 246, 0.3); }}
        .badge-source {{ background: #1F2937; color: #E5E7EB; border: 1px solid #4B5563; }}
        .badge-lang {{ background: #374151; color: #D1D5DB; }}
        .badge-skill {{ background: #1E293B; color: #94A3B8; border: 1px solid #334155; font-size: 0.8rem; text-transform: none; }}

        .job-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        }}
        .job-card:hover {{ transform: translateY(-2px); border-color: #4B5563; box-shadow: 0 12px 30px rgba(0,0,0,0.4); }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }}
        .card-badges {{ display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }}
        .job-title {{ font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem; }}
        .job-company {{ color: var(--text-muted); font-size: 0.9rem; font-weight: 500; }}

        .score-circle {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 65px;
            height: 65px;
            border-radius: 50%;
            border: 3px solid;
            background: rgba(0,0,0,0.3);
            flex-shrink: 0;
        }}
        .score-num {{ font-size: 1.1rem; font-weight: 800; line-height: 1; }}
        .score-label {{ font-size: 0.6rem; font-weight: 700; letter-spacing: 0.5px; opacity: 0.8; }}

        .card-meta {{ display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.9rem; color: #D1D5DB; margin-bottom: 1rem; }}
        .skills-row {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }}

        .ai-highlight {{ background: rgba(59, 130, 246, 0.08); border-left: 3px solid var(--primary); padding: 0.6rem 0.85rem; border-radius: 4px; font-size: 0.88rem; color: #93C5FD; margin-bottom: 1rem; }}

        .card-actions {{ display: flex; gap: 0.75rem; flex-wrap: wrap; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            border: none;
        }}
        .btn-primary {{ background: var(--primary); color: #fff; }}
        .btn-primary:hover {{ background: #2563EB; }}
        .btn-outline {{ background: transparent; color: #E5E7EB; border: 1px solid var(--border); }}
        .btn-outline:hover {{ background: var(--surface-hover); }}

        .job-description-drawer {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            font-size: 0.88rem;
            color: #9CA3AF;
            line-height: 1.6;
        }}
        .desc-content {{ max-height: 400px; overflow-y: auto; background: rgba(0,0,0,0.25); padding: 1rem; border-radius: 8px; }}

        .empty-state {{ text-align: center; padding: 4rem 1rem; color: var(--text-muted); font-size: 1.1rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-top">
                <h1>⚡ Auto Job Hunter AI — Reporte Ejecutivo</h1>
                <div class="stats-badge">🎯 {len(jobs)} Vacantes Aprobadas</div>
            </div>
            <div>
                <strong>Roles & Variantes:</strong> {kw_badges}
            </div>
            <div class="header-meta">
                <span>⏱️ Ventana: <strong>Últimas {int(max_hours)} horas</strong></span>
                <span>📍 Ubicación: <strong>{user_location}</strong></span>
                <span>📅 Generado: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong></span>
            </div>
        </header>

        <div class="search-bar-wrap">
            <input type="text" id="liveSearch" class="search-input" placeholder="🔍 Filtrar por puesto, empresa o portal (ej: React, Indeed, Python)..." onkeyup="filterCards()">
        </div>

        <main id="jobCardsContainer">
            {all_cards_rendered}
        </main>
    </div>

    <script>
        function toggleDetails(id) {{
            const el = document.getElementById(id);
            if (el.style.display === 'none' || !el.style.display) {{
                el.style.display = 'block';
            }} else {{
                el.style.display = 'none';
            }}
        }}

        function filterCards() {{
            const query = document.getElementById('liveSearch').value.toLowerCase();
            const cards = document.querySelectorAll('.job-card');
            cards.forEach(card => {{
                const title = card.getAttribute('data-title') || '';
                const company = card.getAttribute('data-company') || '';
                const source = card.getAttribute('data-source') || '';
                const match = title.includes(query) || company.includes(query) || source.includes(query);
                card.style.display = match ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_markdown(
        self,
        target_path: Path,
        jobs: List[Dict[str, Any]],
        keywords: List[str],
        max_hours: float,
        user_location: str
    ):
        md_lines = [
            f"# 🎯 Reporte de Vacantes — Auto Job Hunter AI ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n",
            f"- **Total Vacantes Aprobadas:** `{len(jobs)}`",
            f"- **Ventana de Tiempo:** Últimas `{int(max_hours)} horas`",
            f"- **Ubicación Candidato:** `{user_location}`",
            f"- **Términos de Búsqueda:** {', '.join(keywords)}\n",
            "---\n",
            "| # | Puesto | Empresa | Modalidad | Salario | Match | Portal | Enlace Directo |",
            "| :---: | :--- | :--- | :---: | :--- | :---: | :---: | :---: |"
        ]

        for idx, j in enumerate(jobs, 1):
            title = j.get("title", "").replace("|", "-")
            company = j.get("company", "").replace("|", "-")
            modality = "100% Remoto" if j.get("real_modality") == "REMOTE" else ("Local" if j.get("real_modality") == "ONSITE_LOCAL" else "Híbrido")
            salary = j.get("salary") or "A convenir"
            score = f"{j.get('match_percentage', 90)}%"
            source = j.get("source", "Web")
            url = j.get("url", "#")
            md_lines.append(f"| {idx} | **{title}** | {company} | `{modality}` | {salary} | **{score}** | {source} | [Postularme]({url}) |")

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
