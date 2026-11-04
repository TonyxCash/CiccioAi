"""Build Ciccio's public website-design service page."""
from html import escape
from pathlib import Path
import os
import re


DEFAULT_CONTACT_EMAIL = "ciccio.servizi@proton.me"


def build_offer_page(output_dir="ciccio_output"):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    configured_email = os.getenv("CICCIO_CONTACT_EMAIL", "").strip()
    contact_email = configured_email if re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+", configured_email
    ) else DEFAULT_CONTACT_EMAIL

    email_href = escape(contact_email, quote=True)
    page = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Siti web professionali, moderni e accessibili da smartphone per negozi, ristoranti e piccole attività.">
<meta name="theme-color" content="#101827">
<title>Siti web per piccole attività | Ciccio</title>
<style>
:root{color-scheme:light;--ink:#172033;--muted:#647087;--blue:#315ee8;--paper:#f4f6fb;--line:#e7ebf3}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1040px;margin:auto;padding:26px 18px 64px}
.hero{padding:clamp(30px,7vw,76px);border-radius:28px;background:linear-gradient(135deg,#101827,#243f79);color:#fff}
.eyebrow{color:#b9cbff;text-transform:uppercase;letter-spacing:.13em;font-size:.78rem;font-weight:750}
h1{font-size:clamp(2.3rem,7vw,4.5rem);line-height:1.05;letter-spacing:-.045em;max-width:780px;margin:18px 0}
.hero p{max-width:700px;color:#e0e8fa;font-size:1.12rem}
.button{display:inline-block;background:var(--blue);color:#fff;text-decoration:none;font-weight:750;padding:14px 20px;border-radius:12px;margin-top:12px}
section{background:#fff;margin-top:18px;padding:clamp(22px,5vw,38px);border:1px solid var(--line);border-radius:22px}
h2{font-size:1.65rem;line-height:1.2;margin:0 0 12px}
.intro{color:var(--muted);max-width:760px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-top:20px}
.item{background:#f6f8fc;border:1px solid var(--line);padding:18px;border-radius:16px}
.item h3{margin:0 0 6px;font-size:1.05rem}
.item p{margin:0;color:var(--muted);font-size:.95rem}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.step{padding:18px;border-left:3px solid #9eb5ff;background:#f7f8fc;border-radius:10px}
.step p{margin:6px 0 0;color:var(--muted)}
.note{font-size:.9rem;color:var(--muted)}
footer{padding:24px 4px;color:var(--muted);font-size:.88rem}
</style>
</head>
<body><main>
<header class="hero">
<div class="eyebrow">Ciccio · Soluzioni digitali per attività locali</div>
<h1>Il tuo sito web, fatto per presentare meglio la tua attività.</h1>
<p>Realizziamo siti web moderni e ottimizzati per smartphone per negozi indipendenti, boutique, ristoranti e pizzerie. Una presenza online chiara, con le informazioni che i tuoi clienti cercano.</p>
<a class="button" href="mailto:__EMAIL__?subject=Richiesta%20informazioni%20sito%20web">Parliamo del tuo sito</a>
</header>
<section>
<h2>Cosa possiamo realizzare</h2>
<p class="intro">Partiamo dalle esigenze concrete della tua attività e definiamo insieme struttura, contenuti e funzionalità. Il progetto e il relativo preventivo vengono concordati prima di iniziare.</p>
<div class="grid">
<article class="item"><h3>Sito vetrina</h3><p>Presentazione dell'attività, servizi, orari, posizione e contatti.</p></article>
<article class="item"><h3>Negozio e boutique</h3><p>Catalogo dei prodotti, categorie, immagini e collegamenti per chiedere informazioni.</p></article>
<article class="item"><h3>Ristoranti e pizzerie</h3><p>Menu, galleria, orari, mappa e richieste di prenotazione o contatto.</p></article>
<article class="item"><h3>Esperienza mobile</h3><p>Pagine leggibili e navigabili da smartphone, tablet e computer.</p></article>
</div>
</section>
<section>
<h2>Un percorso semplice</h2>
<div class="steps">
<div class="step"><strong>1. Ci racconti l'attività</strong><p>Capiremo cosa vendi, chi sono i tuoi clienti e cosa deve fare il sito.</p></div>
<div class="step"><strong>2. Prepariamo una proposta</strong><p>Ricevi una struttura suggerita, le funzionalità e un preventivo chiaro.</p></div>
<div class="step"><strong>3. Realizziamo il progetto</strong><p>Si parte solo dopo la tua approvazione di contenuti, tempi e costi.</p></div>
</div>
</section>
<section>
<h2>Richiedi una prima valutazione</h2>
<p class="intro">Scrivici indicando il nome dell'attività, il comune e se hai già un sito. Ti risponderemo per capire se e come possiamo aiutarti. Nessun acquisto o pagamento viene avviato da questa pagina.</p>
<a class="button" href="mailto:__EMAIL__?subject=Valutazione%20sito%20web">Richiedi informazioni</a>
<p class="note">Il preventivo viene concordato caso per caso. Nessuna promessa di vendite, posizionamento o risultati garantiti.</p>
</section>
<footer>Ciccio · Servizi web per piccole attività. Contatti: <a href="mailto:__EMAIL__">__EMAIL__</a></footer>
</main></body></html>"""
    page = page.replace("__EMAIL__", email_href)
    target = root / "offer-page.html"
    target.write_text(page, encoding="utf-8")
    if not target.is_file() or target.stat().st_size < 1000:
        raise OSError("La pagina offerta non è stata creata correttamente.")
    return {
        "created": True,
        "path": str(target),
        "source": "pagina servizi web Ciccio",
        "bytes": target.stat().st_size,
        "contact_email": contact_email,
    }


if __name__ == "__main__":
    result = build_offer_page()
    print("Pagina offerta creata: " + result["path"] + " da " + result["source"])
