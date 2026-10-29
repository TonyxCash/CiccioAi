"""Build a clean, public-facing Ciccio offer page (not the internal launch-kit notes)."""
from html import escape
from pathlib import Path
import os
import re
from urllib.parse import urlparse


def build_offer_page(output_dir="ciccio_output"):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    # The public information page is safe to publish without a launch-kit draft.
    # Draft files are internal work products and must not gate public-page deployment.
    source = None

    contact_email = os.getenv("CICCIO_CONTACT_EMAIL", "").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
        contact_email = ""

    payment_url = os.getenv("CICCIO_PAYMENT_URL", "https://www.paypal.com/ncp/payment/XEKWURGB47CZW").strip()
    parsed = urlparse(payment_url)
    if parsed.scheme != "https" or not parsed.netloc:
        payment_url = ""

    if contact_email:
        contact = (
            '<a class="button" href="mailto:' + escape(contact_email, quote=True)
            + '?subject=Richiesta%20pacchetto%20cinque%20annunci">Richiedi informazioni sul servizio</a>'
        )
    else:
        contact = (
            '<p class="notice">Contatto non ancora configurato: questa pagina è online, '
            'ma non può ancora ricevere richieste. Il titolare deve configurare un indirizzo email pubblico.</p>'
        )

    payment = (
        '<p><a class="button secondary" href="' + escape(payment_url, quote=True)
        + '" rel="nofollow noopener">Vai al pagamento</a></p>'
        if payment_url else ""
    )

    page = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Cinque annunci di prodotti riscritti per presentare meglio i tuoi articoli e venderli online.">
<title>5 annunci ottimizzati per la vendita online | Ciccio</title>
<style>
:root{color-scheme:light;--ink:#172033;--blue:#2857d5;--muted:#5d687d;--paper:#f4f7fc}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:900px;margin:auto;padding:24px 16px 56px}
.hero{padding:clamp(28px,6vw,56px);border-radius:26px;background:linear-gradient(135deg,#172033,#263f78);color:#fff}
.eyebrow{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;font-weight:750;color:#bcd0ff}
h1{font-size:clamp(2rem,7vw,3.6rem);line-height:1.08;letter-spacing:-.03em;margin:14px 0}
.hero p{max-width:650px;color:#e1e8fa;font-size:1.08rem}
.pill{display:inline-block;border:1px solid #9db7ff;border-radius:999px;padding:5px 12px;font-size:.9rem;margin-top:12px}
section{background:#fff;margin-top:18px;padding:clamp(22px,5vw,36px);border-radius:20px;box-shadow:0 8px 30px #1720330b}
h2{line-height:1.2;margin:0 0 16px;font-size:1.5rem}
ul{padding-left:22px}li{margin:8px 0}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.step{background:#f3f6fd;border-radius:14px;padding:16px}
.button{display:inline-block;background:var(--blue);color:white;text-decoration:none;font-weight:700;padding:13px 18px;border-radius:12px;margin-top:8px}
.button.secondary{background:#e8eefc;color:#2449a9}
.notice{background:#fff4d8;border:1px solid #efd48a;border-radius:12px;padding:14px}
.small{font-size:.9rem;color:var(--muted)}
footer{font-size:.85rem;color:var(--muted);padding:20px 4px}
</style>
</head>
<body><main>
<header class="hero">
<div class="eyebrow">Ciccio · Supporto digitale per piccole attività</div>
<h1>5 annunci più chiari, pronti per la vendita online</h1>
<p>Invia le informazioni reali dei tuoi prodotti e ricevi cinque annunci con titoli più efficaci, descrizioni ordinate e parole chiave pertinenti. Pensato per chi vende abbigliamento e altri prodotti online.</p>
<span class="pill">Pacchetto pilota · 5 annunci · 15 €</span>
</header>
<section>
<h2>Cosa ricevi per 15 €</h2>
<ul>
<li>5 titoli chiari e pertinenti per i tuoi prodotti.</li>
<li>5 descrizioni riscritte usando solo le informazioni e le caratteristiche che ci fornisci.</li>
<li>Parole chiave pertinenti per aiutare gli acquirenti a trovare gli annunci.</li>
</ul>
<p class="small">Non sono garantite vendite o risultati specifici. Non inventiamo materiali, taglie, condizioni o caratteristiche: il lavoro si basa sui dati e sulle foto forniti dal cliente.</p>
</section>
<section>
<h2>Come funziona</h2>
<div class="steps">
<div class="step"><strong>1. Invia i dettagli</strong><p>Condividi foto e informazioni dei cinque prodotti.</p></div>
<div class="step"><strong>2. Prepariamo gli annunci</strong><p>Organizziamo titoli, descrizioni e parole chiave senza aggiungere dettagli inventati.</p></div>
<div class="step"><strong>3. Ricevi il testo pronto</strong><p>Ricevi i cinque annunci da copiare e pubblicare sulla piattaforma che preferisci.</p></div>
</div>
</section>
<section>
<h2>Richiedi il pacchetto di 5 annunci</h2>
<p>Prezzo del pacchetto: <strong>15 € per cinque annunci</strong>. Prima di iniziare, confermeremo via email i dettagli e le informazioni necessarie.</p>
__CONTACT__
__PAYMENT__
</section>
<footer>Servizio di ottimizzazione testi per annunci di vendita online. Non sono garantite vendite o risultati specifici.</footer>
</main></body></html>"""
    page = page.replace("__CONTACT__", contact).replace("__PAYMENT__", payment)
    target = root / "offer-page.html"
    target.write_text(page, encoding="utf-8")
    if not target.is_file() or target.stat().st_size < 500:
        raise OSError("La pagina offerta non è stata creata correttamente.")
    return {"created": True, "path": str(target), "source": source.name if source else "pagina informativa predefinita", "bytes": target.stat().st_size}


if __name__ == "__main__":
    result = build_offer_page()
    if result["created"]:
        print("Pagina offerta creata: " + result["path"] + " da " + result["source"])
    else:
        print("Pagina offerta non creata: " + result["reason"])
