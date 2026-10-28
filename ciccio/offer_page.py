"""Build a shareable, self-contained HTML offer page from Ciccio's launch-kit deliverable.

This prepares a page but does not claim it is publicly published or able to accept payments.
"""
from html import escape
from pathlib import Path
import os
import re
from urllib.parse import urlparse


def latest_launch_kit(output_dir="ciccio_output"):
    root = Path(output_dir)
    candidates = [
        p for p in root.glob("*.md")
        if p.is_file() and any(word in p.name.casefold() for word in ("kit-di-lancio", "offerta", "distribuzione-offerta"))
    ]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def inline_markdown(value):
    value = escape(value, quote=True)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*(.+?)\*", r"<em>\1</em>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(
        r"(https?://[^\s<]+)",
        lambda match: '<a href="' + match.group(1).rstrip('.,;:)') + '" rel="nofollow noopener" target="_blank">' + match.group(1).rstrip('.,;:)') + '</a>' + match.group(1)[len(match.group(1).rstrip('.,;:)')):],
        value,
    )
    return value


def markdown_to_html(markdown):
    lines = markdown.splitlines()
    output = []
    paragraph = []
    in_list = False

    def flush_paragraph():
        if paragraph:
            output.append("<p>" + " ".join(inline_markdown(line.strip()) for line in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        if stripped.startswith("#"):
            flush_paragraph()
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            heading = stripped[level:].strip()
            if heading:
                output.append(f"<h{level}>" + inline_markdown(heading) + f"</h{level}>")
            continue
        if stripped.startswith(("- ", "* ", "+ ")):
            flush_paragraph()
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append("<li>" + inline_markdown(stripped[2:].strip()) + "</li>")
            continue
        close_list()
        paragraph.append(stripped)
    flush_paragraph()
    close_list()
    return "\n".join(output)


def build_offer_page(output_dir="ciccio_output"):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    source = latest_launch_kit(root)
    if source is None:
        return {"created": False, "reason": "Nessun kit di lancio trovato; non viene creata un'offerta inventata."}

    raw = source.read_text(encoding="utf-8").strip()
    if not raw:
        return {"created": False, "reason": "Il kit di lancio è vuoto."}

    contact_email = os.getenv("CICCIO_CONTACT_EMAIL", "").strip()
    payment_url = os.getenv("CICCIO_PAYMENT_URL", "").strip()
    if contact_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
        contact_email = ""
    parsed = urlparse(payment_url)
    if parsed.scheme != "https" or not parsed.netloc:
        payment_url = ""

    actions = []
    if contact_email:
        actions.append('<a class="button" href="mailto:' + escape(contact_email, quote=True) + '">Richiedi informazioni</a>')
    if payment_url:
        actions.append('<a class="button secondary" href="' + escape(payment_url, quote=True) + '" rel="nofollow noopener">Acquista</a>')
    action_html = '<nav class="actions">' + "".join(actions) + '</nav>' if actions else (
        '<p class="notice">Pagina pronta per la revisione. Per ricevere richieste o pagamenti serve configurare un contatto pubblico o un checkout verificato.</p>'
    )

    page = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Offerta e materiali preparati da Ciccio.">
<title>Offerta — Ciccio</title>
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f6fb;color:#172033;font:16px/1.7 system-ui,-apple-system,sans-serif}
main{max-width:820px;margin:0 auto;padding:28px 18px 64px}.hero{padding:28px;border-radius:24px;background:#172033;color:#fff;margin-bottom:20px}
.kicker{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;color:#a9c5ff;font-weight:700}
h1{line-height:1.15;font-size:clamp(2rem,6vw,3.4rem);margin:.35em 0}
.card{background:#fff;padding:clamp(20px,5vw,38px);border-radius:20px;box-shadow:0 8px 32px #14213d0d}
h2,h3{line-height:1.25;margin-top:1.7em}a{color:#2458c7;overflow-wrap:anywhere}.actions{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}.button{display:inline-block;padding:12px 18px;border-radius:12px;background:#2458c7;color:#fff;text-decoration:none;font-weight:700}.button.secondary{background:#e9efff;color:#1d459f}
.notice{background:#fff4d6;border:1px solid #f0d58c;padding:14px 16px;border-radius:12px}.foot{font-size:.85rem;color:#5e6678;margin-top:22px}
</style></head><body><main>
<header class="hero"><div class="kicker">Offerta preparata da Ciccio</div><h1>Una proposta concreta, pronta da valutare</h1><p>Consulta i dettagli qui sotto e verifica che il servizio sia adatto alle tue esigenze.</p></header>
<section class="card">""" + markdown_to_html(raw) + action_html + """</section>
<p class="foot">Questa pagina è un materiale di lavoro generato automaticamente. La creazione del file non significa che sia pubblicato online, che il servizio sia stato venduto o che sia stato ricevuto un pagamento. Verifica contenuti, fonti e condizioni prima della pubblicazione.</p>
</main></body></html>"""
    target = root / "offer-page.html"
    target.write_text(page, encoding="utf-8")
    if not target.is_file() or target.stat().st_size < 500:
        raise OSError("La pagina offerta non è stata creata correttamente.")
    return {"created": True, "path": str(target), "source": source.name, "bytes": target.stat().st_size}


if __name__ == "__main__":
    result = build_offer_page()
    if result["created"]:
        print("Pagina offerta creata: " + result["path"] + " da " + result["source"])
    else:
        print("Pagina offerta non creata: " + result["reason"])
