import csv
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ListingAI — Studio annunci",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { color-scheme:dark; --ink:#e7f5f4; --muted:#8ca9b2; --mint:#9df8e8; --mint-strong:#25dfce; --deep:#071a25; --paper:#06131d; --line:#183746; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:radial-gradient(ellipse at 12% 0%,#103b48 0%,#071a25 43%,#06131d 100%); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(6,19,29,.88); }
.block-container { max-width:1240px; padding:1.4rem 1.5rem 3rem; }
[data-testid="stSidebar"] { background:#071a25; border-right:1px solid #183746; }
[data-testid="stSidebar"] > div { padding-top:1.3rem; }
.brand-mark { width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#23dfce,#087c91);color:#05212a;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;box-shadow:0 0 25px #20dcca22; }
.brand-name { font-family:'Manrope',sans-serif;font-size:1.45rem;font-weight:800;letter-spacing:-.7px;color:#f4ffff; }
.brand-sub { color:#8ca9b2;font-size:.82rem;margin-top:-4px; }
.hero { position:relative;overflow:hidden;padding:2rem 2.1rem;border:1px solid #1b5663;border-radius:26px;background:linear-gradient(115deg,#06232f 0%,#075466 60%,#087e84 115%);color:white;margin:0 0 1.4rem;box-shadow:0 18px 55px #0005; }
.hero:after { content:"";position:absolute;width:230px;height:230px;border:1px solid #8cf8e822;border-radius:50%;right:-45px;top:-95px;box-shadow:0 0 0 28px #8cf8e80a,0 0 0 58px #8cf8e808; }
.hero-kicker { text-transform:uppercase;letter-spacing:2px;font-size:.72rem;font-weight:700;color:#6af5e2;margin-bottom:.65rem; }
.hero h1 { font-family:'Manrope',sans-serif;font-size:clamp(1.9rem,4vw,2.8rem);font-weight:800;letter-spacing:-1.5px;line-height:1.12;margin:0 0 .65rem;color:#fff; }
.hero p { max-width:650px;color:#d0f7f4;font-size:1.02rem;line-height:1.6;margin:0; }
.section-title { font-family:'Manrope',sans-serif;font-weight:800;letter-spacing:-.6px;color:#efffff;font-size:1.45rem;margin:.25rem 0 .25rem; }
.section-subtitle { color:#9bb7bf;margin-bottom:1.2rem;font-size:.94rem; }
.eyebrow { color:#47e8d6;text-transform:uppercase;letter-spacing:1.5px;font-size:.7rem;font-weight:800; }
div[data-testid="stMetric"] { background:linear-gradient(145deg,#0d2633,#091d29);border:1px solid #1b3c4b;padding:17px 18px;border-radius:19px;box-shadow:0 7px 22px #0002; }
div[data-testid="stMetric"] label { color:#9bb7bf!important;font-weight:600; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color:#eaffff;font-family:'Manrope',sans-serif;font-weight:800; }
.stTabs [data-baseweb="tab-list"] { gap:7px;background:#091e2a;padding:6px;border:1px solid #183746;border-radius:15px; }
.stTabs [data-baseweb="tab"] { border-radius:11px;padding:10px 16px;height:auto;font-weight:700;color:#9bb7bf; }
.stTabs [aria-selected="true"] { background:#123746!important;color:#7ef8e9!important;box-shadow:0 2px 8px #0003; }
.stTabs [data-baseweb="tab-highlight"] { background:#25dfce;height:3px; }
div.stButton > button, div.stDownloadButton > button, div[data-testid="stFormSubmitButton"] button { border-radius:13px;min-height:2.9rem;font-weight:700;border:1px solid #214555;background:#0b2633;color:#e7ffff;transition:all .15s ease; }
div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] { background:linear-gradient(100deg,#24dfce,#51f0d7);border-color:#25dfce;color:#05212a; }
div.stButton > button:hover, div.stDownloadButton > button:hover { border-color:#25dfce;color:#72f7e8; }
div[data-testid="stForm"] { background:linear-gradient(145deg,#0b202d,#091b27);border:1px solid #1b3d4c;border-radius:21px;padding:1.2rem;box-shadow:0 10px 35px #0002; }
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stTextArea"] textarea { border-radius:12px!important;background:#061722!important;color:#e7ffff!important;border:1px solid #214455!important; }
div[data-baseweb="select"] > div { border-radius:12px;background:#061722;border-color:#214455; }
.stTextInput label, .stNumberInput label, .stTextArea label, .stSelectbox label { color:#c2d9de;font-weight:600; }
.result-card { background:linear-gradient(145deg,#0d2633,#091d29);border:1px solid #1b3c4b;border-radius:21px;padding:1.25rem;margin:.6rem 0; }
.pill { display:inline-block;padding:5px 10px;border-radius:999px;background:#0d3f45;color:#6cf5e1;font-size:.75rem;font-weight:700;border:1px solid #1d6a6d; }
.info-card { background:linear-gradient(145deg,#0d2633,#091d29);border:1px solid #1b3c4b;border-radius:19px;padding:1.1rem 1.2rem;height:100%; }
.info-icon { width:38px;height:38px;border-radius:12px;background:#0b3b46;color:#59f1df;display:flex;align-items:center;justify-content:center;font-size:19px;margin-bottom:.8rem; }
.small-muted { color:#91adb6;font-size:.84rem;line-height:1.5; }
hr { border-color:#183746!important; }
[data-testid="stDataFrame"] { border:1px solid #1b3c4b;border-radius:15px;overflow:hidden; }
.stAlert { border-radius:14px; }
p, label, li { color:inherit; }
[data-testid="stMarkdownContainer"] a { color:#5cf3e0; }
[data-baseweb="input"] { background:#061722; }
@media(max-width:760px) {
 .block-container {padding:.9rem .65rem 2rem;}
 .hero {padding:1.25rem;border-radius:21px;}
 .hero h1 {font-size:1.85rem;}
 .stTabs [data-baseweb="tab"] {padding:9px 9px;font-size:.82rem;}
 div[data-testid="stForm"] {padding:.8rem;}
}
</style>
""", unsafe_allow_html=True)


# --- Supabase: account personali e archivio persistente ---
from supabase import create_client

if "auth_access_token" not in st.session_state:
    st.session_state.auth_access_token = ""
if "auth_refresh_token" not in st.session_state:
    st.session_state.auth_refresh_token = ""
if "auth_user_id" not in st.session_state:
    st.session_state.auth_user_id = ""
if "auth_email" not in st.session_state:
    st.session_state.auth_email = ""
if "db_loaded_for" not in st.session_state:
    st.session_state.db_loaded_for = ""

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    st.error("Configurazione Supabase non trovata. Apri Manage app → Settings → Secrets su Streamlit e verifica SUPABASE_URL e SUPABASE_KEY.")
    st.stop()

if st.session_state.auth_access_token and st.session_state.auth_refresh_token:
    try:
        supabase.auth.set_session(st.session_state.auth_access_token, st.session_state.auth_refresh_token)
        current_user = supabase.auth.get_user()
        if current_user and current_user.user:
            st.session_state.auth_user_id = current_user.user.id
            st.session_state.auth_email = current_user.user.email or st.session_state.auth_email
    except Exception:
        st.session_state.auth_access_token = ""
        st.session_state.auth_refresh_token = ""
        st.session_state.auth_user_id = ""
        st.session_state.db_loaded_for = ""

if not st.session_state.auth_user_id:
    st.markdown("""
    <div style="max-width:980px;margin:.3rem auto 1.2rem;text-align:center">
      <div style="font-size:2.5rem;color:#39e8d6;line-height:1.2">⌁</div>
      <div style="font-family:Manrope,sans-serif;font-size:2.2rem;font-weight:800;letter-spacing:-1px;color:#f4ffff">Listing<span style="color:#35e7d5">AI</span></div>
      <div style="font-size:1.04rem;color:#b7d1d8;margin:.35rem 0 1.1rem">Il tuo studio intelligente per vendere abbigliamento online.</div>
      <div style="display:flex;justify-content:center;gap:9px;flex-wrap:wrap;margin-bottom:1.3rem">
        <span class="pill">✦ Annunci curati</span><span class="pill">▦ Catalogo personale</span><span class="pill">↗ Da iPhone e computer</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown("""
        <div class="hero" style="min-height:340px;display:flex;flex-direction:column;justify-content:center">
          <div class="hero-kicker">IL TUO SELLER STUDIO</div>
          <h1>Crea annunci migliori.<br>Vendi con più ordine.</h1>
          <p>Organizza i tuoi capi, prepara descrizioni chiare e conserva gli annunci nel tuo archivio personale.</p>
          <div style="margin-top:1.5rem;line-height:2;color:#c8f6f0">✓ Testi pronti da rivedere<br>✓ Catalogo personale salvato online<br>✓ Un unico spazio semplice da usare</div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section-title">Bentornato</div><div class="section-subtitle">Accedi o crea il tuo account gratuito.</div>', unsafe_allow_html=True)
        auth_mode = st.radio("Scegli un’opzione", ["Accedi", "Crea account"], horizontal=True, label_visibility="collapsed", key="auth_mode")
        if auth_mode == "Accedi":
            with st.form("login_form"):
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")
                login_submit = st.form_submit_button("Accedi", type="primary", use_container_width=True)
            if login_submit:
                try:
                    result = supabase.auth.sign_in_with_password({"email": login_email.strip(), "password": login_password})
                    st.session_state.auth_access_token = result.session.access_token
                    st.session_state.auth_refresh_token = result.session.refresh_token
                    st.session_state.auth_user_id = result.user.id
                    st.session_state.auth_email = result.user.email or login_email.strip()
                    st.session_state.db_loaded_for = ""
                    st.rerun()
                except Exception:
                    st.error("Accesso non riuscito. Controlla email e password e verifica l'email se la registrazione lo richiede.")
        else:
            with st.form("register_form"):
                register_email = st.text_input("La tua email", key="register_email")
                register_password = st.text_input("Crea una password (almeno 6 caratteri)", type="password", key="register_password")
                register_password_confirm = st.text_input("Ripeti la password", type="password", key="register_password_confirm")
                register_submit = st.form_submit_button("Crea account", type="primary", use_container_width=True)
            if register_submit:
                if register_password != register_password_confirm:
                    st.error("Le due password non coincidono.")
                elif len(register_password) < 6:
                    st.error("Scegli una password di almeno 6 caratteri.")
                else:
                    try:
                        result = supabase.auth.sign_up({"email": register_email.strip(), "password": register_password})
                        if result.session:
                            st.session_state.auth_access_token = result.session.access_token
                            st.session_state.auth_refresh_token = result.session.refresh_token
                            st.session_state.auth_user_id = result.user.id
                            st.session_state.auth_email = result.user.email or register_email.strip()
                            st.session_state.db_loaded_for = ""
                            st.rerun()
                        else:
                            st.success("Account creato. Controlla la tua email per confermare la registrazione, poi seleziona Accedi.")
                    except Exception:
                        st.error("Registrazione non riuscita. Controlla l'email: potrebbe essere già registrata.")
        st.caption("Usa una password dedicata a ListingAI. Non riutilizzare password importanti.")
    st.stop()


with st.sidebar:
    st.markdown('<div style="display:flex;gap:11px;align-items:center"><div class="brand-mark">✳</div><div><div class="brand-name">ListingAI</div><div class="brand-sub">Seller studio</div></div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**IL TUO SPAZIO DI LAVORO**")
    st.caption("Crea annunci migliori, organizza i capi e prepara i testi da pubblicare.")
    st.markdown("---")
    st.markdown('<span class="pill">✦ Archivio personale</span>', unsafe_allow_html=True)
    st.caption(st.session_state.auth_email)
    admin_email = str(st.secrets.get("ADMIN_EMAIL", "")).strip().lower()
    is_admin = bool(admin_email) and st.session_state.auth_email.strip().lower() == admin_email
    if is_admin:
        st.markdown('<span class="pill">✦ AMMINISTRATORE</span>', unsafe_allow_html=True)
    if st.button("Esci dall’account", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        for key in ("auth_access_token", "auth_refresh_token", "auth_user_id", "auth_email", "db_loaded_for", "items", "generated"):
            st.session_state.pop(key, None)
        st.rerun()
    st.markdown("<div class='small-muted' style='margin-top:12px'>Gli annunci salvati vengono conservati nel database del tuo account.</div>", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Il tuo studio per vendere meglio</div>
  <h1>Meno tempo a scrivere.<br>Più spazio alle vendite.</h1>
  <p>Trasforma i dettagli dei tuoi capi in annunci curati, coerenti e pronti da adattare al marketplace. Tutto in un unico spazio semplice da usare.</p>
</div>
""", unsafe_allow_html=True)

if "generated" not in st.session_state:
    st.session_state.generated = None

# Carica dal database una sola volta per account/sessione.
if st.session_state.db_loaded_for != st.session_state.auth_user_id:
    try:
        response = supabase.table("listings").select("*").eq("user_id", st.session_state.auth_user_id).order("created_at", desc=True).execute()
        st.session_state.items = []
        for row in (response.data or []):
            st.session_state.items.append({
                "id": row.get("id"),
                "user_id": row.get("user_id"),
                "title": row.get("title") or "",
                "description": row.get("description") or "",
                "hashtags": row.get("hashtags") or "",
                "category": row.get("category") or "Altro",
                "brand": row.get("brand") or "",
                "size": row.get("size") or "",
                "color": row.get("color") or "",
                "condition": row.get("condition") or "",
                "material": row.get("material") or "",
                "details": row.get("details") or "",
                "price": float(row.get("price") or 0),
                "platform": row.get("platform") or "",
                "created": row.get("created_at") or "",
                "cost": 0.0,
            })
        st.session_state.db_loaded_for = st.session_state.auth_user_id
    except Exception as e:
        st.error("Non riesco a leggere il catalogo da Supabase. Verifica che supabase_schema.sql sia stato eseguito e che le policy RLS siano attive. Dettaglio: " + str(e))
        st.session_state.items = []

CATEGORIES = ["Jeans", "Pantaloni", "T-shirt", "Camicia", "Felpa", "Giacca", "Cappotto", "Scarpe", "Abito", "Borsa", "Accessori", "Altro"]
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
    title = " ".join(x for x in title_parts if x).strip() or "Articolo di abbigliamento"
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
    seen, hashtags = set(), []
    for tag in tags:
        normalized = re.sub(r"[^a-zA-Z0-9àèéìòù]", "", tag.lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            hashtags.append("#" + normalized)
    return title, "\n".join(lines), " ".join(hashtags[:12])

def money(value):
    return f"€{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

total_items = len(st.session_state.items)
total_value = sum(float(x.get("price", 0)) for x in st.session_state.items)
k1, k2, k3 = st.columns(3)
k1.metric("Capi nel catalogo", total_items)
k2.metric("Valore richiesto", money(total_value))
k3.metric("Studio", "Pronto", help="Puoi iniziare senza configurare chiavi API.")

admin_email = str(st.secrets.get("ADMIN_EMAIL", "")).strip().lower()
is_admin = bool(admin_email) and st.session_state.auth_email.strip().lower() == admin_email
tab_names = ["✳ Crea annuncio", "▦ Catalogo", "ⓘ Guida rapida"]
if is_admin:
    tab_names.append("⚙ Admin")
tab_list = st.tabs(tab_names)
tab_create, tab_catalog, tab_help = tab_list[0], tab_list[1], tab_list[2]
if is_admin:
    tab_admin = tab_list[3]

with tab_create:
    st.markdown('<div class="section-title">Crea il tuo prossimo annuncio</div><div class="section-subtitle">Inserisci le informazioni essenziali: ListingAI prepara una prima bozza che puoi rifinire.</div>', unsafe_allow_html=True)
    with st.form("listing_form", clear_on_submit=False):
        st.markdown('<div class="eyebrow">01 / Dettagli del capo</div>', unsafe_allow_html=True)
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
            tone = st.selectbox("Tono dell'annuncio", ["Naturale", "Essenziale", "Elegante"])
            keywords = st.text_input("Parole chiave", placeholder="Es. sartoriale, slim fit")
        details = st.text_area("Dettagli da valorizzare", placeholder="Vestibilità, misure, modello, particolari o eventuali difetti da segnalare…", height=110)
        submitted = st.form_submit_button("✦ Genera la bozza", type="primary", use_container_width=True)
    if submitted:
        item = {"category":category, "brand":clean(brand), "size":clean(size), "color":clean(color), "condition":condition, "price":float(price), "cost":float(cost), "material":clean(material), "details":clean(details), "tone":tone, "keywords":clean(keywords), "created":datetime.now().strftime("%Y-%m-%d %H:%M")}
        title, description, hashtags = make_listing(item, tone, keywords)
        st.session_state.generated = {"item":item, "title":title, "description":description, "hashtags":hashtags}
        st.session_state.pop("edit_title", None)
        st.session_state.pop("edit_description", None)
        st.session_state.pop("edit_hashtags", None)

    generated = st.session_state.generated
    if generated:
        st.markdown("---")
        st.markdown('<div class="section-title">La tua bozza è pronta</div><div class="section-subtitle">Rivedi e modifica ogni campo prima di copiarlo o scaricarlo.</div>', unsafe_allow_html=True)
        g1, g2 = st.columns([1.7, 1])
        with g1:
            title = st.text_input("Titolo", value=generated["title"], key="edit_title", max_chars=100)
            description = st.text_area("Descrizione", value=generated["description"], height=230, key="edit_description")
            hashtags = st.text_input("Hashtag", value=generated["hashtags"], key="edit_hashtags")
            full_text = f"{title}\n\n{description}\n\n{hashtags}"
            st.code(full_text, language=None)
            st.download_button("↓ Scarica annuncio .txt", data=full_text, file_name="annuncio_listingai.txt", mime="text/plain", use_container_width=True)
        with g2:
            item = generated["item"]
            st.markdown('<div class="result-card"><div class="eyebrow">RIEPILOGO</div>', unsafe_allow_html=True)
            st.metric("Prezzo richiesto", money(item["price"]))
            if item["cost"] > 0:
                st.metric("Differenza prezzo / costo", money(item["price"] - item["cost"]))
                st.caption("Differenza lorda: non include commissioni, spedizione o imposte.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('<div class="info-card"><div class="eyebrow">PROSSIMO PASSO</div><p style="margin-top:10px"><b>Controlla, copia e pubblica</b></p><p class="small-muted">Verifica taglia, condizioni, marca e prezzo. La bozza non viene pubblicata automaticamente.</p></div>', unsafe_allow_html=True)
            if st.button("＋ Salva nel catalogo", type="primary", use_container_width=True):
                try:
                    payload = {
                        "user_id": st.session_state.auth_user_id,
                        "title": title,
                        "description": description,
                        "hashtags": hashtags,
                        "category": item.get("category", ""),
                        "brand": item.get("brand", ""),
                        "size": item.get("size", ""),
                        "color": item.get("color", ""),
                        "condition": item.get("condition", ""),
                        "material": item.get("material", ""),
                        "details": item.get("details", ""),
                        "price": float(item.get("price", 0)),
                        "platform": "",
                    }
                    supabase.table("listings").insert(payload).execute()
                    st.session_state.db_loaded_for = ""
                    st.success("Annuncio salvato nel database del tuo account.")
                    st.rerun()
                except Exception as e:
                    st.error("Salvataggio non riuscito. Verifica tabella e policy Supabase. Dettaglio: " + str(e))
            if st.button("Crea un'altra bozza", use_container_width=True):
                st.session_state.generated = None
                for key in ("edit_title", "edit_description", "edit_hashtags"):
                    st.session_state.pop(key, None)
                st.rerun()
    else:
        st.markdown("---")
        a, b, c = st.columns(3)
        with a:
            st.markdown('<div class="info-card"><div class="info-icon">✍️</div><b>Testi più ordinati</b><p class="small-muted">Titolo, descrizione e hashtag in un formato pronto da rivedere.</p></div>', unsafe_allow_html=True)
        with b:
            st.markdown('<div class="info-card"><div class="info-icon">◈</div><b>Il tuo stile</b><p class="small-muted">Scegli un tono naturale, essenziale o elegante.</p></div>', unsafe_allow_html=True)
        with c:
            st.markdown('<div class="info-card"><div class="info-icon">▦</div><b>Catalogo esportabile</b><p class="small-muted">Salva le bozze e scarica i dati in formato CSV.</p></div>', unsafe_allow_html=True)

with tab_catalog:
    st.markdown('<div class="section-title">Il tuo catalogo</div><div class="section-subtitle">Tieni sotto controllo gli annunci salvati nel tuo account.</div>', unsafe_allow_html=True)
    items = st.session_state.items
    if not items:
        st.info("Il catalogo è vuoto. Crea un annuncio e scegli «Salva nel catalogo» per iniziare. Gli annunci salvati resteranno nel tuo account.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Annunci salvati", len(items))
        m2.metric("Valore richiesto totale", money(sum(float(x.get("price", 0)) for x in items)))
        rows = [{"Titolo":x.get("title",""), "Categoria":x.get("category",""), "Taglia":x.get("size",""), "Colore":x.get("color",""), "Prezzo":float(x.get("price",0)), "Condizioni":x.get("condition","")} for x in items]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        st.download_button("↓ Esporta catalogo CSV", csv_buffer.getvalue().encode("utf-8-sig"), "catalogo_listingai.csv", "text/csv", use_container_width=True)
        options = {f"{x.get('title','Articolo')} · {money(x.get('price',0))}":x.get("id") for x in items}
        selected_label = st.selectbox("Seleziona un annuncio da eliminare", list(options.keys()))
        if st.button("Elimina annuncio selezionato"):
            try:
                supabase.table("listings").delete().eq("id", options[selected_label]).eq("user_id", st.session_state.auth_user_id).execute()
                st.session_state.db_loaded_for = ""
                st.rerun()
            except Exception as e:
                st.error("Eliminazione non riuscita. Dettaglio: " + str(e))

with tab_help:
    st.markdown('<div class="section-title">ListingAI, in breve</div><div class="section-subtitle">Le funzioni disponibili oggi e cosa svilupperemo dopo.</div>', unsafe_allow_html=True)
    h1, h2 = st.columns(2)
    with h1:
        st.markdown('<div class="info-card"><div class="info-icon">✦</div><b>Generazione della bozza</b><p class="small-muted">Questa versione usa modelli di testo locali inclusi nel codice: non utilizza un servizio AI esterno e non richiede chiavi API.</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card" style="margin-top:14px"><div class="info-icon">▦</div><b>Catalogo temporaneo</b><p class="small-muted">Gli annunci salvati sono conservati nel database associato al tuo account.</p></div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="info-card"><div class="info-icon">↗</div><b>Pubblicazione manuale</b><p class="small-muted">ListingAI non accede agli account marketplace e non pubblica annunci in automatico. Copia la bozza e controllala prima di usarla.</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card" style="margin-top:14px"><div class="info-icon">⌁</div><b>Prossime evoluzioni</b><p class="small-muted">Database persistente, account personali, gestione immagini, strumenti di prezzo e piani a pagamento sono sviluppi successivi, da testare prima del lancio commerciale.</p></div>', unsafe_allow_html=True)
    st.warning("Le descrizioni sono bozze automatiche basate sui dati inseriti. Controlla che ogni affermazione sia vera, soprattutto per marca, autenticità, condizioni e materiali.")

if is_admin:
    with tab_admin:
        st.markdown('<div class="section-title">Pannello amministratore</div><div class="section-subtitle">Area riservata all’indirizzo autorizzato nelle Secrets di Streamlit.</div>', unsafe_allow_html=True)
        st.success("Accesso amministratore riconosciuto.")
        a1, a2, a3 = st.columns(3)
        a1.metric("I tuoi annunci salvati", len(st.session_state.items))
        a2.metric("Valore del tuo catalogo", money(sum(float(x.get("price", 0)) for x in st.session_state.items)))
        a3.metric("Stato database", "Connesso", help="La lettura del catalogo è riuscita in questa sessione.")
        st.markdown('<div class="info-card"><div class="eyebrow">GESTIONE PRODOTTO</div><p style="margin-top:10px"><b>Prossimi moduli amministrativi</b></p><p class="small-muted">Questa prima area admin verifica il tuo ruolo e mostra lo stato del tuo catalogo. Gestione utenti, piani, pagamenti e statistiche globali richiederanno endpoint e autorizzazioni server-side dedicati: non vengono abilitati con una semplice verifica email.</p></div>', unsafe_allow_html=True)
        st.caption("Email amministratore configurata: " + admin_email)

st.markdown("---")
st.markdown('<div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><span class="small-muted"><b>ListingAI</b> · Seller studio</span><span class="small-muted">Prototipo in sviluppo · Non affiliato ufficialmente a Vinted o altri marketplace</span></div>', unsafe_allow_html=True)
