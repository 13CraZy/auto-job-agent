import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path
from src.llm.client import LLMMatchResult
from src.compiler.sanitizer import escape_latex, format_bullet_points

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_TECTONIC = BASE_DIR / "bin" / "tectonic.exe"

def get_tectonic_cmd() -> str:
    """Busca el ejecutable de Tectonic en bin/ local o en el PATH."""
    if LOCAL_TECTONIC.exists():
        return str(LOCAL_TECTONIC)
    cmd = shutil.which("tectonic") or shutil.which("pdflatex")
    return cmd or ""

async def compile_tex_file(tex_path: Path, output_dir: Path) -> Path:
    """Compila un archivo .tex a .pdf."""
    tectonic_cmd = get_tectonic_cmd()
    pdf_path = output_dir / f"{tex_path.stem}.pdf"

    if not tectonic_cmd:
        print(f"[Compiler] AVISO: Compilador LaTeX no encontrado. .tex disponible en: {tex_path}")
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write("% PDF Placeholder (Compiler missing)")
        return pdf_path

    is_tectonic = "tectonic" in tectonic_cmd.lower()
    if is_tectonic:
        cmd = [tectonic_cmd, "-o", str(output_dir), str(tex_path)]
    else:
        cmd = [tectonic_cmd, f"-output-directory={output_dir}", "-interaction=nonstopmode", str(tex_path)]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        print(f"[Compiler] Advertencia durante compilación de {tex_path.name}: {stderr.decode()}")
    else:
        print(f"[Compiler] PDF generado exitosamente: {pdf_path.name}")

    return pdf_path

async def generate_and_compile_latex(
    cv_template_path: Path,
    cl_template_path: Path,
    output_dir: Path,
    file_prefix: str,
    user_profile: dict,
    llm_result: LLMMatchResult,
    job_posting: dict
) -> tuple[Path, Path, Path, Path]:
    """
    Inyecta los datos adaptados bilingües en las plantillas de CV y Cover Letter,
    aplicando el Título pivotado (Backend/Frontend/Full Stack) y la Fórmula XYZ de Google.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    personal = user_profile.get("personal_info", {})
    lang = llm_result.target_language
    company = job_posting.get("company", "Company")
    candidate_title = llm_result.candidate_title or "Full Stack Software Engineer"

    # ================= 1. RENDEREAR CV (GARANTÍA 1 PÁGINA) =================
    with open(cv_template_path, "r", encoding="utf-8") as f:
        cv_tex_content = f.read()

    if lang == "en":
        sec_summary, sec_skills, sec_exp, sec_proj, sec_edu = "Professional Summary", "Technical Skills", "Professional Experience", "Featured Engineering Projects", "Education"
        cat_lang, cat_backend, cat_frontend, cat_db, cat_devops = "Languages & Web Frameworks", "Backend, Cloud & IoT", "Frontend & UI Engineering", "Databases & Caching", "Infrastructure, DevSecOps & AI Tools"
    else:
        sec_summary, sec_skills, sec_exp, sec_proj, sec_edu = "Resumen Profesional", "Habilidades Técnicas", "Experiencia Profesional", "Proyectos Tecnológicos Core", "Educación"
        cat_lang, cat_backend, cat_frontend, cat_db, cat_devops = "Lenguajes y Frameworks Web", "Backend, Cloud e IoT", "Frontend e Ingeniería de UI", "Bases de Datos y Caché", "Infraestructura, DevSecOps y Herramientas AI"

    cv_tex_content = cv_tex_content.replace("{{ SECTION_SUMMARY_TITLE }}", escape_latex(sec_summary))
    cv_tex_content = cv_tex_content.replace("{{ SECTION_SKILLS_TITLE }}", escape_latex(sec_skills))
    cv_tex_content = cv_tex_content.replace("{{ SECTION_EXPERIENCE_TITLE }}", escape_latex(sec_exp))
    cv_tex_content = cv_tex_content.replace("{{ SECTION_PROJECTS_TITLE }}", escape_latex(sec_proj))
    cv_tex_content = cv_tex_content.replace("{{ SECTION_EDUCATION_TITLE }}", escape_latex(sec_edu))

    cv_tex_content = cv_tex_content.replace("{{ SKILL_CAT_LANG }}", escape_latex(cat_lang))
    cv_tex_content = cv_tex_content.replace("{{ SKILL_CAT_BACKEND }}", escape_latex(cat_backend))
    cv_tex_content = cv_tex_content.replace("{{ SKILL_CAT_FRONTEND }}", escape_latex(cat_frontend))
    cv_tex_content = cv_tex_content.replace("{{ SKILL_CAT_DATABASE }}", escape_latex(cat_db))
    cv_tex_content = cv_tex_content.replace("{{ SKILL_CAT_DEVOPS }}", escape_latex(cat_devops))

    edu_blocks = []
    for edu in user_profile.get("education", []):
        inst = escape_latex(edu.get("institution", ""))
        deg = escape_latex(edu.get("degree", ""))
        per = escape_latex(edu.get("period", ""))
        loc = escape_latex(edu.get("location", ""))
        loc_str = f" \\hfill \\small {loc}" if loc else ""
        per_str = f" \\hfill \\small {per}" if per else ""
        edu_blocks.append(f"    \\item \\small \\textbf{{{inst}}}{loc_str}\\\\\n    \\small \\textit{{{deg}}}{per_str}")

    cv_tex_content = cv_tex_content.replace("{{ EDUCATION_BLOCK }}", "\n".join(edu_blocks))

    raw_name = personal.get("name", "Candidate")
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', raw_name)

    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_NAME }}", escape_latex(raw_name))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_TITLE }}", escape_latex(candidate_title))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_LOCATION }}", escape_latex(personal.get("location", "")))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_EMAIL }}", escape_latex(personal.get("email", "")))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_PHONE }}", escape_latex(personal.get("phone", "")))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_GITHUB }}", escape_latex(personal.get("github", "")))
    cv_tex_content = cv_tex_content.replace("{{ PERSONAL_LINKEDIN }}", escape_latex(personal.get("linkedin", "")))
    cv_tex_content = cv_tex_content.replace("{{ PROFESSIONAL_SUMMARY }}", escape_latex(llm_result.professional_summary))

    skills = llm_result.skills_category_highlighted
    cv_tex_content = cv_tex_content.replace("{{ SKILLS_LANGUAGES }}", escape_latex(", ".join(skills.languages)))
    cv_tex_content = cv_tex_content.replace("{{ SKILLS_BACKEND }}", escape_latex(", ".join(skills.backend)))
    cv_tex_content = cv_tex_content.replace("{{ SKILLS_FRONTEND }}", escape_latex(", ".join(skills.frontend)))
    cv_tex_content = cv_tex_content.replace("{{ SKILLS_DATABASE }}", escape_latex(", ".join(skills.database)))
    cv_tex_content = cv_tex_content.replace("{{ SKILLS_DEVOPS }}", escape_latex(", ".join(skills.devops_cloud)))

    exp_blocks = []
    for exp in llm_result.experiences:
        company_escaped = escape_latex(exp.company)
        role_escaped = escape_latex(exp.role)
        bullets_formatted = format_bullet_points(exp.bullet_points)
        period_escaped = escape_latex(exp.period or "")
        location_escaped = escape_latex(exp.location or "")

        block = f"""\\noindent \\small \\textbf{{{role_escaped}}} \\hfill \\small \\textbf{{{period_escaped}}}\\\\
\\small \\textit{{{company_escaped}}} \\hfill \\small \\textit{{{location_escaped}}}\\\\
{bullets_formatted}
\\vspace{{1pt}}"""
        exp_blocks.append(block)

    cv_tex_content = cv_tex_content.replace("{{ EXPERIENCES_BLOCK }}", "\n".join(exp_blocks))

    proj_blocks = []
    projects = llm_result.projects if llm_result.projects else user_profile.get("projects", [])
    for proj in projects:
        name_val = proj.name if hasattr(proj, 'name') else proj.get("name", "")
        tech_val = proj.tech_stack if hasattr(proj, 'tech_stack') else proj.get("tech_stack", "")
        period_val = proj.period if hasattr(proj, 'period') else proj.get("period", "")
        bullets_val = proj.bullet_points if hasattr(proj, 'bullet_points') else proj.get("bullet_points", [])

        name_escaped = escape_latex(name_val)
        tech_escaped = escape_latex(tech_val)
        period_escaped = escape_latex(period_val)
        bullets_formatted = format_bullet_points(bullets_val)

        block = f"""\\noindent \\small \\textbf{{{name_escaped}}} \\textbar{{}} \\textit{{{tech_escaped}}} \\hfill \\small \\textbf{{{period_escaped}}}\\\\
{bullets_formatted}
\\vspace{{1pt}}"""
        proj_blocks.append(block)

    cv_tex_content = cv_tex_content.replace("{{ PROJECTS_BLOCK }}", "\n".join(proj_blocks))

    cv_tex_filename = f"CV_{safe_name}_{file_prefix}_{lang.upper()}.tex"
    cv_tex_filepath = output_dir / cv_tex_filename
    with open(cv_tex_filepath, "w", encoding="utf-8") as f:
        f.write(cv_tex_content)

    cv_pdf_filepath = await compile_tex_file(cv_tex_filepath, output_dir)

    # ================= 2. RENDEREAR COVER LETTER =================
    cl_tex_filepath = output_dir / f"Cover_Letter_{safe_name}_{file_prefix}_{lang.upper()}.tex"
    cl_pdf_filepath = output_dir / f"Cover_Letter_{safe_name}_{file_prefix}_{lang.upper()}.pdf"
    cl_md_filepath = output_dir / f"cover_letter_{lang.upper()}.md"

    if cl_template_path.exists():
        with open(cl_template_path, "r", encoding="utf-8") as f:
            cl_tex_content = f.read()

        hiring_title = "Hiring Manager / Recruitment Team" if lang == "en" else "Equipo de Selección de Personal"
        closing_salutation = "Sincerely" if lang == "en" else "Atentamente"
        date_str = datetime.now().strftime("%B %d, %Y") if lang == "en" else datetime.now().strftime("%d de %B de %Y")

        cl_body_escaped = escape_latex(llm_result.cover_letter_body).replace("\n\n", "\n\n\\par ")

        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_NAME }}", escape_latex(raw_name))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_TITLE }}", escape_latex(candidate_title))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_LOCATION }}", escape_latex(personal.get("location", "")))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_EMAIL }}", escape_latex(personal.get("email", "")))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_PHONE }}", escape_latex(personal.get("phone", "")))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_GITHUB }}", escape_latex(personal.get("github", "")))
        cl_tex_content = cl_tex_content.replace("{{ PERSONAL_LINKEDIN }}", escape_latex(personal.get("linkedin", "")))
        cl_tex_content = cl_tex_content.replace("{{ DATE_STR }}", date_str)
        cl_tex_content = cl_tex_content.replace("{{ HIRING_TITLE }}", hiring_title)
        cl_tex_content = cl_tex_content.replace("{{ COMPANY_NAME }}", escape_latex(company))
        cl_tex_content = cl_tex_content.replace("{{ COVER_LETTER_BODY }}", cl_body_escaped)
        cl_tex_content = cl_tex_content.replace("{{ CLOSING_SALUTATION }}", closing_salutation)

        with open(cl_tex_filepath, "w", encoding="utf-8") as f:
            f.write(cl_tex_content)

        cl_pdf_filepath = await compile_tex_file(cl_tex_filepath, output_dir)

    with open(cl_md_filepath, "w", encoding="utf-8") as f:
        f.write(f"# Cover Letter - {company}\n\n")
        f.write(llm_result.cover_letter_body)

    return cv_tex_filepath, cv_pdf_filepath, cl_tex_filepath, cl_pdf_filepath
