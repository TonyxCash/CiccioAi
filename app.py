import csv
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ListingAI", page_icon="🧥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root { color-scheme: light; }
.block-container {max-width: 1120px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.7rem; border-radius: 22px; background: linear-gradient(120deg,#17152b,#39316b 65%,#8068c8); color:white; margin-bottom:1.3rem;}
.hero h1 {font-size:2.3rem; margin:0 0 .35rem 0; color:white;}
.hero p {margin:0; color:#e8e4ff; font-size:1.02rem;}
div[data-testid="stMetric"] {background:#f7f6fc; border:1px solid #e8e5f2; padding:14px 16px; border-radius:16px;}
div.stButton > button, div.stDownloadButton > button {border-radius:12px; min-height:2.8rem; font-weight:600;}
div[data-testid="stForm"] {border:1px solid #e8e5f2; border-radius:18px; padding:1rem;}
.small-muted {color:#77738b; font-size:.9rem;}
@media (max-width: 640px) {.block-container {padding:1rem .8rem 2rem;} .hero {padding:1.2rem;} .hero h1 {font-size:1.8rem;}}
</style>
<div class="hero">
  <h1>🧥 ListingAI</h1>
  <p>Da informazioni sul capo a un annuncio pronto da pubblicare.</p>
</div>
""", unsafe_allow_html=True)

st.caption("MVP gratuito · Nessun account richiesto · I dati restano nella sessione corrente")

if "items" not in st.session_state:
    st.session_state.items = []
if "generated" not in st.session_state:
    st.session_state.generated = None

CATEGORIES = ["Jeans", "Pantaloni", "T-shirt", "Camicia", "Felpa", "Giacca", "Cappotto", "Scarpe", "Abito", "Altro"]
CONDITIONS = ["Nuovo con etichette", "Nuovo senza etichette", "Ottime condizioni", "Buone condizioni", "Condizioni accettabili"]

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def make_listing(item, tone, keywords):
    brand = clean(item.get("brand")) or "Senza marca indicata"
    category = clean(item.get("category")) or "Abbigliamento"
    size = clean(item.get("size")) or "Non indicata"
    color = clean(item.get("color")) or "Non indicato"
    condition = clean(item.get("condition")) or "Non specificate"
    material = clean(item.get("material"))
    details = clean(item.get("details"))
    price = float(item.get("price") or 0)
    title_parts = [brand if brand != "Senza marca indicata" else "", category, color if color != "Non indicato" else "", f"taglia {size}" if size != "Non indicata" else ""]
    title = " ".join(x for x in title_parts if x).strip()
    if not title:
        title = "Articolo di abbigliamento"
    title = title[:100]
    if tone == "Essenziale":
        intro = f"{category} {('di ' + brand) if brand != 'Senza marca indicata' else ''}, colore {color.lower()}."
    elif tone == "Elegante":
        intro = f"Un capo {category.lower()} dal look curato{(' firmato ' + brand) if brand != 'Senza marca indicata' else ''}, facile da abbinare."
    else:
        intro = f"In vendita: {category.lower()}{(' ' + brand) if brand != 'Senza marca indicata' else ''}, ideale per completare i tuoi outfit."
    lines = [intro, f"• Taglia: {size}", f"• Colore: {color}", f"• Condizioni: {condition}"]
    if material:
        lines.append(f"• Materiale: {material}")
    if details:
        lines.append(f"• Dettagli: {details}")
    lines += ["", "Guarda le foto per tutti i dettagli e scrivimi se vuoi altre informazioni."]
    if price > 0:
        lines += ["", f"Prezzo richiesto: €{price:.2f}".replace(".", ",")]
    tags = [category, brand, color, "abbigliamento", "secondamano", "outfit"]
    if keywords:
        tags += [x.strip().lstrip("#") for x in keywords.split(",") if x.strip()]
    seen = set()
    hashtags = []
    for tag in tags:
        normalized = re.sub(r"[^a-zA-Z0-9àèéìòù]", "", tag.lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            hashtags.append("#" + normalized)
    return title, "\n".join(lines), " ".join(hashtags[:12])

def money(value):
    return f"€{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

tab_create, tab_catalog, tab_help = st.tabs(["✨ Crea annuncio", "📦 Il mio catalogo", "ℹ️ Come funziona"])

with tab_create:
    st.subheader("Descrivi il tuo capo")
    st.write("Inserisci i dettagli una volta: prepariamo titolo, descrizione e hashtag modificabili.")
    with st.form("listing_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Categoria *", CATEGORIES)
            brand = st.text_input("Marca", placeholder="Es. Levi's, Zara, Jhavè")
            size = st.text_input("Taglia", placeholder="Es. 48, M, XL")
            color = st.text_input("Colore", placeholder="Es. blu scuro")
            condition = st.selectbox("Condizioni", CONDITIONS)
        with c2:
            price = st.number_input("Prezzo richiesto (€)", min_value=0.0, max_value=100000.0, value=39.99, step=1.0)
            cost = st.number_input("Costo per te (€) — facoltativo", min_value=0.0, max_value=100000.0, value=0.0, step=1.0)
            material = st.text_input("Materiale", placeholder="Es. 97% cotone, 3% elastan")
            tone = st.selectbox("Stile del testo", ["Naturale", "Essenziale", "Elegante"])
            keywords = st.text_input("Parole chiave aggiuntive", placeholder="Es. sartoriale, slim fit")
        details = st.text_area("Dettagli del capo", placeholder="Vestibilità, misure, modello, difetti o particolari da segnalare…", height=100)
        submitted = st.form_submit_button("Genera annuncio", type="primary", use_container_width=True)
    if submitted:
        item = {"category":category, "brand":clean(brand), "size":clean(size), "color":clean(color), "condition":condition, "price":float(price), "cost":float(cost), "material":clean(material), "details":clean(details), "tone":tone, "keywords":clean(keywords), "created":datetime.now().strftime("%Y-%m-%d %H:%M")}
        title, description, hashtags = make_listing(item, tone, keywords)
        st.session_state.generated = {"item":item, "title":title, "description":description, "hashtags":hashtags}
    generated = st.session_state.generated
    if generated:
        st.divider()
        st.subheader("Il tuo annuncio")
        st.caption("Controlla sempre le informazioni prima di pubblicare. Non vengono verificati automaticamente marca, condizioni o prezzi di mercato.")
        g1, g2 = st.columns([2,1])
        with g1:
            title = st.text_input("Titolo (modificabile)", value=generated["title"], key="edit_title")
            description = st.text_area("Descrizione (modificabile)", value=generated["description"], height=230, key="edit_description")
            hashtags = st.text_input("Hashtag (modificabili)", value=generated["hashtags"], key="edit_hashtags")
            full_text = f"{title}\n\n{description}\n\n{hashtags}"
            st.code(full_text, language=None)
            st.download_button("⬇️ Scarica annuncio .txt", data=full_text, file_name="annuncio_listingai.txt", mime="text/plain", use_container_width=True)
        with g2:
            item = generated["item"]
            st.metric("Prezzo richiesto", money(item["price"]))
            if item["cost"] > 0:
                st.metric("Differenza prezzo/costo", money(item["price"]-item["cost"]))
                st.caption("Differenza lorda, non include commissioni, spedizione o imposte.")
            st.write("**Pronto per:**")
            st.write("• Copia e incolla nel marketplace")
            st.write("• Modifica il testo prima di pubblicare")
            if st.button("💾 Salva nel catalogo", type="primary", use_container_width=True):
                saved = dict(item)
                saved.update({"title":title, "description":description, "hashtags":hashtags, "id":datetime.now().strftime("%Y%m%d%H%M%S%f")})
                st.session_state.items.insert(0, saved)
                st.success("Annuncio salvato nel catalogo per questa sessione.")
            if st.button("Nuovo annuncio", use_container_width=True):
                st.session_state.generated = None
                st.rerun()

with tab_catalog:
    st.subheader("Il mio catalogo")
    items = st.session_state.items
    if not items:
        st.info("Non hai ancora salvato annunci. Crea un annuncio e premi «Salva nel catalogo».")
    else:
        total_value = sum(float(x.get("price",0)) for x in items)
        m1, m2 = st.columns(2)
        m1.metric("Annunci salvati", len(items))
        m2.metric("Valore richiesto totale", money(total_value))
        rows = []
        for x in items:
            rows.append({"Titolo":x.get("title",""), "Categoria":x.get("category",""), "Taglia":x.get("size",""), "Colore":x.get("color",""), "Prezzo":float(x.get("price",0)), "Condizioni":x.get("condition","")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        st.download_button("⬇️ Esporta catalogo CSV", csv_buffer.getvalue().encode("utf-8-sig"), "catalogo_listingai.csv", "text/csv", use_container_width=True)
        options = {f"{x.get('title','Articolo')} · {money(x.get('price',0))}":x.get("id") for x in items}
        selected_label = st.selectbox("Seleziona un annuncio da eliminare", list(options.keys()))
        if st.button("Elimina annuncio selezionato"):
            st.session_state.items = [x for x in items if x.get("id") != options[selected_label]]
            st.rerun()

with tab_help:
    st.subheader("Una prima versione semplice")
    st.markdown("""
- **Generazione locale:** il testo viene creato da modelli inclusi nell'app; non serve una chiave API.
- **Nessuna pubblicazione automatica:** copi tu l'annuncio e lo controlli prima di pubblicarlo.
- **Nessun accesso a Vinted:** l'app non richiede le credenziali dei marketplace.
- **Privacy:** in questa versione catalogo e annuncio salvato vivono nella sessione Streamlit; possono andare persi quando la sessione si riavvia.
- **Prezzi:** la differenza tra costo e prezzo non è un utile netto e non include commissioni o imposte.
    """)
    st.info("Questo è un prototipo MVP. Login, database persistente, piani Pro e pagamenti verranno aggiunti solo dopo i primi test con utenti reali.")

st.divider()
st.markdown('<p class="small-muted">ListingAI · MVP in sviluppo · Nessuna affiliazione ufficiale con Vinted o altri marketplace.</p>', unsafe_allow_html=True)
