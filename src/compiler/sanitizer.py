import re

def escape_latex(text: str) -> str:
    """Escapa caracteres especiales de LaTeX para evitar rupturas en la compilación."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    chars_map = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    
    pattern = re.compile(r'(?<!\\)([' + re.escape(''.join(chars_map.keys())) + r'])')
    text = pattern.sub(lambda m: chars_map[m.group(1)], text)
    
    text = text.replace('“', "``").replace('”', "''").replace('"', "''")
    return text

def format_bullet_points(bullets: list[str]) -> str:
    """Formatea una lista de balazos en un entorno itemize ultracompacto para 1 página."""
    items = []
    if bullets:
        for bullet in bullets:
            b_str = bullet.strip() if isinstance(bullet, str) else str(bullet)
            if b_str:
                safe_bullet = escape_latex(b_str)
                items.append(f"    \\item \\small {safe_bullet}")
    if not items:
        items.append("    \\item \\small Desempeñé funciones de desarrollo y arquitectura de software adaptadas a la vacante.")
    return "\\begin{itemize}[leftmargin=*,noitemsep,topsep=1pt,parsep=0pt,partopsep=0pt]\n" + "\n".join(items) + "\n\\end{itemize}"
