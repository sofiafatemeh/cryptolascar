"""
delivery/email.py — Envoi d'emails HTML via Gmail SMTP et archivage Markdown.

Threat model:
  T-04-01 : smtp_password jamais loggé — seuls report_type, len(recipients), str(e)
             apparaissent dans les logs en cas d'échec.
  T-04-02 : Archivage avant envoi — si archive échoue, l'email n'est pas envoyé.
"""
from __future__ import annotations

import email.charset
import quopri
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import Config
from logging_setup import get_logger

logger = get_logger(__name__)

# Répertoire racine des templates (relatif à ce fichier)
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

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
    """
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("## "):
            html_lines.append(
                f"<h2 style=\"color:#1a1a2e;font-size:18px;margin-top:24px;\">{line[3:]}</h2>"
            )
        elif line.startswith("# "):
            html_lines.append(
                f"<h1 style=\"color:#1a1a2e;font-size:22px;\">{line[2:]}</h1>"
            )
        elif line.strip() == "":
            html_lines.append("")
        else:
            html_lines.append(line)
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
        OSError: si l'écriture échoue (re-raise après log)
    """
    dest = Path("reports") / report_type / f"{date}.md"
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

    # Conversion Markdown -> HTML pour le corps du template
    body_html = _markdown_to_html(plain_text)

    # Rendu Jinja2 (D-01, D-02, D-06)
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    template = env.get_template("report_email.html")
    html_content = template.render(subject=subject, body_html=body_html)

    # Construction du message MIME multipart/alternative (REPT-05, D-03)
    # Forcer quoted-printable sur la partie HTML pour que msg.as_string() reste lisible.
    # La partie text/plain utilise utf-8 standard (les tests cherchent le texte brut).
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.smtp_user
    msg["To"] = ", ".join(config.recipient_list)

    plain_part = MIMEText(plain_text, "plain", "utf-8")

    # Partie HTML : forcer quoted-printable pour que les accents restent lisibles
    # dans msg.as_string() sans encodage base64 opaque.
    html_encoded = quopri.encodestring(html_content.encode("utf-8")).decode("ascii")
    html_part = MIMEText("", "html")
    html_part.set_payload(html_encoded)
    html_part["Content-Transfer-Encoding"] = "quoted-printable"
    html_part.set_charset("utf-8")
    # Remplacer le Content-Type généré automatiquement par set_charset()
    if "Content-Type" in html_part:
        del html_part["Content-Type"]
    html_part["Content-Type"] = 'text/html; charset="utf-8"'

    msg.attach(plain_part)
    msg.attach(html_part)

    try:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
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
