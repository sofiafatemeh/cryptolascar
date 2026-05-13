"""
delivery/email.py — Envoi d'emails HTML via Gmail SMTP et archivage Markdown.

Threat model:
  T-04-01 : smtp_password jamais loggé — seuls report_type, len(recipients), str(e)
             apparaissent dans les logs en cas d'échec.
  T-04-02 : Archivage avant envoi — si archive échoue, l'email n'est pas envoyé.
"""
from __future__ import annotations

import html as html_stdlib
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import Config
from logging_setup import get_logger

logger = get_logger(__name__)

# Répertoire racine du projet et des templates (relatif à ce fichier)
_PROJECT_ROOT = Path(__file__).parent.parent
_TEMPLATES_DIR = _PROJECT_ROOT / "templates"
_REPORTS_DIR = _PROJECT_ROOT / "reports"

# Validation des paramètres d'entrée (CR-02)
_SAFE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFE_TYPE_RE = re.compile(r"^(daily|weekly|monthly)$")

# Environnement Jinja2 module-level avec autoescape activé (CR-01, WR-01)
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

# Patterns de sujet par type de rapport (D-05)
_SUBJECTS = {
    "daily": "[DAILY] Analyse du {date}",
    "weekly": "[WEEKLY WRAP] Bilan de la semaine {date}",
    "monthly": "[MONTHLY CLOSE] Bilan du mois {month} {year}",
}


def build_subject(
    report_type: str,
    date: str,
    month: str = "",
    year: str = "",
) -> str:
    """Construit la ligne de sujet selon le type de rapport (D-05).

    Args:
        report_type: "daily" | "weekly" | "monthly"
        date: date ISO YYYY-MM-DD
        month: nom du mois en français (monthly uniquement)
        year: année en 4 chiffres (monthly uniquement)

    Returns:
        str: sujet formaté
    """
    template = _SUBJECTS.get(report_type, "[REPORT] {date}")
    return template.format(date=date, month=month, year=year)


def _markdown_to_html(text: str) -> str:
    """Conversion minimale Markdown -> HTML pour le template email.

    Transforme ## Titre -> <h2>Titre</h2> et les paragraphes en <p>.
    Pas de bibliothèque externe — inline uniquement (D-02).
    Le contenu des titres et lignes normales est HTML-échappé (CR-01).
    """
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("## "):
            safe_content = html_stdlib.escape(line[3:])
            html_lines.append(
                f'<h2 style="color:#1a1a2e;font-size:18px;margin-top:24px;">{safe_content}</h2>'
            )
        elif line.startswith("# "):
            safe_content = html_stdlib.escape(line[2:])
            html_lines.append(
                f'<h1 style="color:#1a1a2e;font-size:22px;">{safe_content}</h1>'
            )
        elif line.strip() == "":
            html_lines.append("")
        else:
            html_lines.append(html_stdlib.escape(line))
    # Joindre, puis entourer les blocs de texte en <p>
    raw = "\n".join(html_lines)
    # Remplacer les doubles sauts de ligne entre texte par </p><p>
    raw = re.sub(r"\n{2,}", "</p><p>", raw)
    return f"<p>{raw}</p>"


def archive_report(report_type: str, date: str, content: str) -> None:
    """Archive le rapport en Markdown avant envoi email (D-13, STOR-01).

    Args:
        report_type: "daily" | "weekly" | "monthly"
        date: date ISO YYYY-MM-DD (ex: "2026-05-10")
        content: texte brut du rapport (sortie reporters)

    Raises:
        ValueError: si report_type ou date ne respectent pas le format attendu (CR-02)
        OSError: si l'écriture échoue (re-raise après log)
    """
    # Validation des paramètres pour prévenir le path traversal (CR-02)
    if not _SAFE_TYPE_RE.match(report_type):
        raise ValueError(f"Invalid report_type: {report_type!r}")
    if not _SAFE_DATE_RE.match(date):
        raise ValueError(f"Invalid date format: {date!r}")

    dest = _REPORTS_DIR / report_type / f"{date}.md"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        logger.info("Report archived: %s", dest)
    except OSError as e:
        logger.error(
            "Archive failed: report_type=%s date=%s error=%s",
            report_type, date, str(e),
        )
        raise


def send_email(
    report_type: str,
    date: str,
    plain_text: str,
    config: Config,
    month: str = "",
    year: str = "",
) -> None:
    """Envoie le rapport par email HTML via Gmail SMTP (D-04, REPT-05).

    Args:
        report_type: "daily" | "weekly" | "monthly"
        date: date ISO YYYY-MM-DD
        plain_text: texte brut du rapport (text/plain fallback, D-03)
        config: Config avec champs SMTP et recipient_list
        month: nom du mois en français (pour monthly uniquement)
        year: année (pour monthly uniquement)

    Raises:
        Exception: toute erreur SMTP est loggée puis re-levée (D-07)
    """
    subject = build_subject(report_type, date, month=month, year=year)

    # Conversion Markdown -> HTML pour le corps du template (contenu HTML-échappé)
    body_html = _markdown_to_html(plain_text)

    # Rendu Jinja2 avec autoescape activé (CR-01, WR-01)
    # body_html est pré-construit et de confiance → | safe dans le template
    # subject est auto-échappé par autoescape=True
    template = _JINJA_ENV.get_template("report_email.html")
    html_content = template.render(subject=subject, body_html=body_html)

    # Construction du message MIME multipart/alternative (REPT-05, D-03)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.smtp_user
    msg["To"] = ", ".join(config.recipient_list)

    plain_part = MIMEText(plain_text, "plain", "utf-8")

    # Partie HTML : MIMEText gère l'encodage automatiquement (CR-03)
    # Évite le double Content-Transfer-Encoding causé par set_charset() après
    # une assignation manuelle du header (violation RFC 2045).
    html_part = MIMEText(html_content, "html", "utf-8")

    msg.attach(plain_part)
    msg.attach(html_part)

    try:
        if config.smtp_port == 465:
            ctx = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port)
            ctx.login(config.smtp_user, config.smtp_password)
            ctx.sendmail(config.smtp_user, config.recipient_list, msg.as_string())
            ctx.quit()
        else:
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(config.smtp_user, config.smtp_password)
                smtp.sendmail(
                    config.smtp_user,
                    config.recipient_list,
                    msg.as_string(),
                )
        logger.info(
            "Email sent: report_type=%s date=%s recipients=%d",
            report_type, date, len(config.recipient_list),
        )
    except Exception as e:
        # T-04-01 : smtp_password JAMAIS loggé
        logger.error(
            "Email send failed: report_type=%s recipients=%d error=%s",
            report_type, len(config.recipient_list), str(e),
        )
        raise
