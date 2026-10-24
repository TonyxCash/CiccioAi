import csv
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from urllib.parse import parse_qsl
from streamlit_url_fragment import get_fragment

st.set_page_config(
    page_title="ListingAI — Studio annunci",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root{color-scheme:light;--ink:#191827;--muted:#62647a;--line:#e7e7f0;--violet:#6848f5}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;-webkit-font-smoothing:antialiased}
.stApp{background:#f7f7fb!important;color:#191827!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"],section.main{background:#f7f7fb!important;color:#191827!important}
[data-testid="stHeader"]{background:rgba(247,247,251,.96)!important}
.block-container{max-width:1240px;padding:1.1rem 1.15rem 3rem}
[data-testid="stSidebar"]{background:#fff!important;border-right:1px solid #e8e8f1}
[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#252438}
[data-testid="stMarkdownContainer"] a{color:#6246e8!important}
h1,h2,h3,h4{color:#191827!important;font-family:'Manrope',sans-serif!important;letter-spacing:-.7px}
label,[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p{color:#38374d!important}

.login-brand{max-width:980px;margin:.3rem auto 1.4rem;text-align:center;padding:1.25rem 1rem 1.1rem;background:linear-gradient(135deg,#fff 0%,#f3f0ff 58%,#fff0f5 100%);border:1px solid #e7e2fb;border-radius:24px;box-shadow:0 12px 34px #32206b0b}
.login-brand-symbol{font-size:1.6rem;line-height:1.2;color:#6848f5!important;margin-bottom:.35rem}
.login-brand-name{font-family:'Manrope',sans-serif;font-size:clamp(2rem,6vw,2.65rem);font-weight:800;letter-spacing:-1.3px;line-height:1.15;color:#191827!important}
.login-brand-name span{color:#6848f5!important}
.login-brand-subtitle{font-size:1rem;color:#55566d!important;line-height:1.5;margin:.55rem 0 1rem}
.login-brand-pills{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}
.login-brand-pills span{display:inline-flex;padding:7px 11px;border-radius:999px;background:#fff;color:#51436f!important;border:1px solid #e6e0f8;font-size:.78rem;font-weight:700}
@media(max-width:760px){.login-brand{padding:1.1rem .7rem;border-radius:19px;margin:.1rem auto 1rem}.login-brand-subtitle{font-size:.92rem}.login-brand-pills span{font-size:.72rem;padding:6px 9px}}
.brand-mark{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#ff648c,#8058f5 65%,#5275ff);color:#fff!important;display:inline-flex;align-items:center;justify-content:center;font-size:23px;font-weight:800;box-shadow:0 7px 20px #7357ff25}
.brand-name{font-family:'Manrope',sans-serif;font-size:1.4rem;font-weight:800;letter-spacing:-.7px;color:#191827!important}
.brand-sub,.small-muted{color:#62647a!important;font-size:.85rem;line-height:1.55}
.hero{position:relative;overflow:hidden;padding:1.8rem 1.7rem;border-radius:24px;background:linear-gradient(115deg,#4e3bd8,#7457f7 60%,#986bff);color:#fff!important;margin:0 0 1.3rem;box-shadow:0 15px 38px #6548e51c}
.hero *{color:#fff!important}.hero-kicker{font-size:.7rem;font-weight:800;letter-spacing:1.7px;margin-bottom:.65rem;color:#ffe5ef!important}
.hero h1{font-size:clamp(1.8rem,4vw,2.7rem);font-weight:800;line-height:1.12;margin:0 0 .65rem;color:#fff!important}
.hero p{max-width:650px;color:#fff!important;font-size:1rem;line-height:1.6;margin:0}
.section-title{font-family:'Manrope',sans-serif;font-weight:800;color:#191827!important;font-size:1.45rem;margin:.3rem 0}
.section-subtitle{color:#62647a!important;margin-bottom:1.1rem;font-size:.94rem;line-height:1.55}
.eyebrow{color:#6848f5!important;text-transform:uppercase;letter-spacing:1.5px;font-size:.7rem;font-weight:800}
div[data-testid="stMetric"]{background:#fff!important;border:1px solid #e7e7f0;padding:16px;border-radius:18px;box-shadow:0 5px 18px #19163306}
div[data-testid="stMetric"] label,div[data-testid="stMetric"] label p{color:#62647a!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#211c42!important;font-family:'Manrope',sans-serif;font-weight:800}
.stTabs [data-baseweb="tab-list"]{display:flex;flex-wrap:wrap;gap:5px;background:#efedf8;padding:5px;border:1px solid #e7e3f4;border-radius:15px;white-space:normal}
.stTabs [data-baseweb="tab"]{flex:1 1 auto;white-space:normal;min-width:max-content;border-radius:11px;padding:10px 12px;height:auto;font-weight:700;color:#49475f!important}
.stTabs [data-baseweb="tab"] p{color:inherit!important}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:#fff!important;color:#5c43e8!important;box-shadow:0 2px 8px #20134a0d}
.stTabs [data-baseweb="tab-highlight"]{background:#7357ff;height:3px;border-radius:3px}
div.stButton>button,div.stDownloadButton>button,div[data-testid="stFormSubmitButton"] button{border-radius:12px;min-height:2.8rem;font-weight:700;border:1px solid #e2e1ed;background:#fff!important;color:#39364f!important}
div.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"] button[kind="primary"]{background:#6848f5!important;border-color:#6848f5!important;color:#fff!important;box-shadow:0 5px 14px #7357ff24}
div[data-testid="stForm"]{background:#fff!important;border:1px solid #e7e7f0;border-radius:19px;padding:1rem;box-shadow:0 8px 28px #19163305}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stTextArea"] textarea{border-radius:12px!important;background:#fff!important;color:#191827!important;border:1px solid #d6d6e3!important;min-height:2.8rem}
div[data-testid="stTextInput"] input::placeholder,div[data-testid="stTextArea"] textarea::placeholder{color:#77778b!important;opacity:1!important}
div[data-baseweb="select"]>div{border-radius:12px;background:#fff!important;border-color:#d6d6e3}
div[data-baseweb="select"] input,div[data-baseweb="select"] span{color:#191827!important}
.result-card,.info-card{background:#fff!important;border:1px solid #e7e7f0;border-radius:19px;padding:1.1rem;margin:.6rem 0;box-shadow:0 7px 24px #19163305}
.pill{display:inline-block;padding:5px 10px;border-radius:999px;background:#f3efff;color:#5e43e8!important;font-size:.75rem;font-weight:700;border:1px solid #e5ddff}
.info-icon{width:40px;height:40px;border-radius:13px;background:#f0eaff;color:#6848f5!important;display:flex;align-items:center;justify-content:center;font-size:19px;margin-bottom:.8rem}
hr{border-color:#e9e9f1!important}
[data-testid="stDataFrame"]{border:1px solid #e7e7f0;border-radius:14px;overflow:hidden}
.stAlert{border-radius:14px}
@media(max-width:760px){.block-container{padding:.8rem .65rem 2rem}.hero{padding:1.35rem 1.15rem;border-radius:20px}.hero h1{font-size:1.85rem;letter-spacing:-1px}.hero p{font-size:.93rem}.stTabs [data-baseweb="tab-list"]{gap:4px}.stTabs [data-baseweb="tab"]{padding:8px 9px;font-size:.8rem}.stTabs [data-baseweb="tab-list"] button{flex:1 1 42%}div[data-testid="stForm"]{padding:.8rem}div[data-testid="stMetric"]{padding:12px}}
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

# --- Recupero password: il link email deve riportare token_hash e type=recovery nella query ---
if "recovery_verified" not in st.session_state:
    st.session_state.recovery_verified = False

# Supabase può restituire i token nella parte #fragment dell'URL.
# st.query_params non legge il fragment: lo recuperiamo dal browser.
try:
    browser_fragment = get_fragment()
    if browser_fragment:
        fragment_params = dict(parse_qsl(str(browser_fragment).lstrip("#")))
        if fragment_params.get("type") == "recovery" and not st.session_state.recovery_verified:
            fragment_access_token = fragment_params.get("access_token", "")
            fragment_refresh_token = fragment_params.get("refresh_token", "")
            if fragment_access_token and fragment_refresh_token:
                supabase.auth.set_session(fragment_access_token, fragment_refresh_token)
                fragment_user = supabase.auth.get_user()
                if fragment_user and fragment_user.user:
                    st.session_state.auth_access_token = fragment_access_token
                    st.session_state.auth_refresh_token = fragment_refresh_token
                    st.session_state.auth_user_id = fragment_user.user.id
                    st.session_state.auth_email = fragment_user.user.email or ""
                    st.session_state.recovery_verified = True
                    st.rerun()
except Exception:
    pass

# Supabase può usare il flusso PKCE e tornare all'app con ?code=...
# Scambiamo il codice con una sessione prima di mostrare la schermata di login.
try:
    auth_code = st.query_params.get("code", "")
except Exception:
    auth_code = ""

if auth_code and not st.session_state.recovery_verified:
    try:
        code_result = supabase.auth.exchange_code_for_session(auth_code)
        if code_result.session and code_result.user:
            st.session_state.auth_access_token = code_result.session.access_token
            st.session_state.auth_refresh_token = code_result.session.refresh_token
            st.session_state.auth_user_id = code_result.user.id
            st.session_state.auth_email = code_result.user.email or ""
            st.session_state.recovery_verified = True
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Il link non ha restituito una sessione valida. Richiedi una nuova email di recupero.")
            st.stop()
    except Exception:
        st.error("Non riesco a completare il link di recupero. Potrebbe essere scaduto o già utilizzato. Richiedi una nuova email e aprila subito.")
        st.stop()

try:
    recovery_token_hash = st.query_params.get("token_hash", "") or st.query_params.get("token", "")
    recovery_type = st.query_params.get("type", "")
except Exception:
    recovery_token_hash = ""
    recovery_type = ""

if recovery_token_hash and recovery_type == "recovery" and not st.session_state.recovery_verified:
    try:
        recovery_result = supabase.auth.verify_otp({
            "token_hash": recovery_token_hash,
            "type": "recovery",
        })
        if recovery_result.session and recovery_result.user:
            st.session_state.auth_access_token = recovery_result.session.access_token
            st.session_state.auth_refresh_token = recovery_result.session.refresh_token
            st.session_state.auth_user_id = recovery_result.user.id
            st.session_state.auth_email = recovery_result.user.email or ""
            st.session_state.recovery_verified = True
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Il link di recupero non è valido o è scaduto. Richiedi una nuova email.")
            st.stop()
    except Exception:
        st.error("Non riesco a verificare il link di recupero. Potrebbe essere scaduto o già utilizzato. Richiedi un nuovo link.")
        st.stop()

if st.session_state.recovery_verified:
    st.markdown('<div class="section-title">Imposta una nuova password</div><div class="section-subtitle">Il link è stato verificato. Scegli una password nuova per ListingAI.</div>', unsafe_allow_html=True)
    with st.form("complete_password_recovery_form"):
        new_password = st.text_input("Nuova password (almeno 6 caratteri)", type="password")
        confirm_new_password = st.text_input("Ripeti la nuova password", type="password")
        save_new_password = st.form_submit_button("Salva nuova password", type="primary", use_container_width=True)
    if save_new_password:
        if len(new_password) < 6:
            st.error("La password deve contenere almeno 6 caratteri.")
        elif new_password != confirm_new_password:
            st.error("Le due password non coincidono.")
        else:
            try:
                # Streamlit riesegue lo script a ogni invio del modulo:
                # ripristina la sessione Supabase salvata prima di aggiornare la password.
                saved_access_token = st.session_state.get("auth_access_token", "")
                saved_refresh_token = st.session_state.get("auth_refresh_token", "")
                if not saved_access_token or not saved_refresh_token:
                    raise RuntimeError("La sessione di recupero non è più disponibile. Riapri un link di recupero recente.")
                supabase.auth.set_session(saved_access_token, saved_refresh_token)
                supabase.auth.update_user({"password": new_password})
                st.session_state.recovery_verified = False
                st.session_state.auth_access_token = ""
                st.session_state.auth_refresh_token = ""
                st.session_state.auth_user_id = ""
                st.session_state.auth_email = ""
                st.session_state.db_loaded_for = ""
                st.success("Password aggiornata. Ora puoi accedere con la nuova password.")
                st.rerun()
            except Exception as error:
                st.error("Non è stato possibile aggiornare la password.")
                with st.expander("Dettagli tecnici dell’errore — mandami uno screenshot di questo riquadro"):
                    st.code(str(error))
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
    <div class="login-brand">
      <div class="login-brand-symbol">✳</div>
      <div class="login-brand-name">Listing<span>AI</span></div>
      <div class="login-brand-subtitle">Il tuo studio intelligente per vendere abbigliamento online.</div>
      <div class="login-brand-pills">
        <span>✦ Annunci curati</span><span>▦ Catalogo personale</span><span>↗ Da iPhone e computer</span>
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
        auth_mode = st.radio(
            "Scegli un’opzione",
            ["Accedi", "Crea account", "Password dimenticata?"],
            horizontal=True,
            label_visibility="collapsed",
            key="auth_mode",
        )

        if auth_mode == "Accedi":
            with st.form("login_form"):
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")
                login_submit = st.form_submit_button("Accedi", type="primary", use_container_width=True)
            if login_submit:
                if not login_email.strip() or not login_password:
                    st.error("Inserisci email e password.")
                else:
                    try:
                        result = supabase.auth.sign_in_with_password(
                            {"email": login_email.strip(), "password": login_password}
                        )
                        if not result.session or not result.user:
                            st.error("Accesso non completato. Verifica email e password e riprova.")
                        else:
                            st.session_state.auth_access_token = result.session.access_token
                            st.session_state.auth_refresh_token = result.session.refresh_token
                            st.session_state.auth_user_id = result.user.id
                            st.session_state.auth_email = result.user.email or login_email.strip()
                            st.session_state.db_loaded_for = ""
                            st.rerun()
                    except Exception as error:
                        st.error("Accesso non riuscito. Controlla email, password e conferma dell'email.")
                        with st.expander("Dettagli tecnici dell'errore"):
                            st.code(str(error))

        elif auth_mode == "Crea account":
            with st.form("register_form"):
                register_email = st.text_input("La tua email", key="register_email")
                register_password = st.text_input("Crea una password (almeno 6 caratteri)", type="password", key="register_password")
                register_password_confirm = st.text_input("Ripeti la password", type="password", key="register_password_confirm")
                register_submit = st.form_submit_button("Crea account", type="primary", use_container_width=True)
            if register_submit:
                if not register_email.strip() or "@" not in register_email:
                    st.error("Inserisci un indirizzo email valido.")
                elif register_password != register_password_confirm:
                    st.error("Le due password non coincidono.")
                elif len(register_password) < 6:
                    st.error("Scegli una password di almeno 6 caratteri.")
                else:
                    try:
                        result = supabase.auth.sign_up(
                            {"email": register_email.strip(), "password": register_password}
                        )
                        if result.session and result.user:
                            st.session_state.auth_access_token = result.session.access_token
                            st.session_state.auth_refresh_token = result.session.refresh_token
                            st.session_state.auth_user_id = result.user.id
                            st.session_state.auth_email = result.user.email or register_email.strip()
                            st.session_state.db_loaded_for = ""
                            st.rerun()
                        else:
                            st.success("Account creato. Controlla la posta per confermare l'email, poi torna qui e accedi.")
                    except Exception as error:
                        st.error("Registrazione non riuscita. Controlla l'email: potrebbe essere già registrata o il servizio email potrebbe essere limitato.")
                        with st.expander("Dettagli tecnici dell'errore"):
                            st.code(str(error))

        else:
            st.markdown(
                "Inserisci l'email associata al tuo account. Se il servizio email è configurato, "
                "Supabase invierà le istruzioni per reimpostare la password."
            )
            with st.form("password_reset_form"):
                reset_email = st.text_input("Email dell'account", key="reset_email")
                reset_submit = st.form_submit_button(
                    "Invia link di recupero", type="primary", use_container_width=True
                )
            if reset_submit:
                if not reset_email.strip() or "@" not in reset_email:
                    st.error("Inserisci un indirizzo email valido.")
                else:
                    try:
                        supabase.auth.reset_password_for_email(reset_email.strip())
                        st.success(
                            "Richiesta inviata. Se l'email è registrata e il servizio email è configurato, "
                            "riceverai un messaggio. Controlla anche Spam/Indesiderata."
                        )
                    except Exception as error:
                        st.error("Supabase non è riuscito a inviare il link di recupero.")
                        with st.expander("Dettagli tecnici dell'errore"):
                            st.code(str(error))

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
        st.session_state["items"] = []
        for row in (response.data or []):
            st.session_state["items"].append({
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
                "status": row.get("status") or "Da pubblicare",
                "created": row.get("created_at") or "",
                "cost": 0.0,
            })
        st.session_state.db_loaded_for = st.session_state.auth_user_id
    except Exception as e:
        st.error("Non riesco a leggere il catalogo da Supabase. Verifica che supabase_schema.sql sia stato eseguito e che le policy RLS siano attive. Dettaglio: " + str(e))
        st.session_state["items"] = []

CATEGORIES = ["Jeans", "Pantaloni", "T-shirt", "Camicia", "Felpa", "Giacca", "Cappotto", "Scarpe", "Abito", "Borsa", "Accessori", "Altro"]
CONDITIONS = ["Nuovo con etichette", "Nuovo senza etichette", "Ottime condizioni", "Buone condizioni", "Condizioni accettabili"]

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def make_listing(item, tone, keywords):
    brand = clean(item.get("brand"))
    category = clean(item.get("category")) or "Abbigliamento"
    size = clean(item.get("size"))
    color = clean(item.get("color"))
    condition = clean(item.get("condition"))
    material = clean(item.get("material"))
    details = clean(item.get("details"))
    price = float(item.get("price") or 0)
    fit = clean(item.get("fit"))
    style = clean(item.get("style"))
    platform = clean(item.get("platform")) or "Generico"

    # Titolo leggibile, senza aggiungere informazioni non fornite.
    title_parts = [brand, category, color, fit, f"taglia {size}" if size else ""]
    title = " ".join(x for x in title_parts if x).strip() or "Articolo di abbigliamento"
    title = re.sub(r"\\s+", " ", title)[:100].strip()

    if tone == "Essenziale":
        intro = f"{category}{(' di ' + brand) if brand else ''}{(', colore ' + color.lower()) if color else ''}."
    elif tone == "Elegante":
        intro = f"Capo {category.lower()}{(' di ' + brand) if brand else ''}, dal look curato e facile da abbinare."
    else:
        intro = f"In vendita: {category.lower()}{(' ' + brand) if brand else ''}{(' in colore ' + color.lower()) if color else ''}."

    lines = [intro, ""]
    facts = []
    if size:
        facts.append(f"Taglia: {size}")
    if color:
        facts.append(f"Colore: {color}")
    if condition:
        facts.append(f"Condizioni: {condition}")
    if material:
        facts.append(f"Materiale: {material}")
    if fit:
        facts.append(f"Vestibilità: {fit}")
    if style:
        facts.append(f"Stile: {style}")
    if details:
        facts.append(f"Dettagli: {details}")
    lines.extend(f"• {fact}" for fact in facts)

    if platform == "Vinted":
        lines += ["", "Guarda le foto per valutare il capo. Se ti servono altre misure o informazioni, scrivimi pure."]
    elif platform == "eBay":
        lines += ["", "Leggi i dettagli e controlla taglia e condizioni prima dell'acquisto. Le informazioni riportate si riferiscono al capo descritto."]
    elif platform == "Subito":
        lines += ["", "Per ulteriori informazioni o per chiarire i dettagli dell'articolo, contattami tramite la piattaforma."]
    elif platform == "Facebook Marketplace":
        lines += ["", "Se vuoi altre informazioni sul capo, mandami un messaggio."]
    else:
        lines += ["", "Per altre informazioni o foto aggiuntive, scrivimi pure."]

    if price > 0:
        lines += ["", f"Prezzo richiesto: €{price:.2f}".replace(".", ",")]

    base_tags = {
        "Vinted": [category, brand, color, "secondamano", "preloved", "outfit"],
        "eBay": [category, brand, color, "abbigliamento", "moda", "taglia" + size if size else ""],
        "Subito": [category, brand, color, "abbigliamento", "usato", "affare"],
        "Facebook Marketplace": [category, brand, color, "abbigliamento", "moda", "outfit"],
    }
    tags = base_tags.get(platform, [category, brand, color, "abbigliamento", "secondamano", "outfit"])
    if keywords:
        tags += [x.strip().lstrip("#") for x in keywords.split(",") if x.strip()]
    seen, hashtags = set(), []
    for tag in tags:
        normalized = re.sub(r"[^a-zA-Z0-9àèéìòù]", "", tag.lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            hashtags.append("#" + normalized)
    return title, "\\n".join(lines), " ".join(hashtags[:12])

def money(value):
    return f"€{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

catalog_items = st.session_state["items"]
total_items = len(catalog_items)
total_value = sum(float(x.get("price", 0) or 0) for x in catalog_items)
to_publish = sum(1 for x in catalog_items if (x.get("status") or "Da pubblicare") == "Da pubblicare")
published = sum(1 for x in catalog_items if (x.get("status") or "Da pubblicare") == "Pubblicato")
sold = sum(1 for x in catalog_items if (x.get("status") or "Da pubblicare") == "Venduto")
sold_value = sum(float(x.get("price", 0) or 0) for x in catalog_items if (x.get("status") or "Da pubblicare") == "Venduto")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Capi nel catalogo", total_items)
k2.metric("Da pubblicare", to_publish)
k3.metric("Pubblicati", published)
k4.metric("Venduti", sold)
k5.metric("Valore richiesto", money(total_value), help="Somma dei prezzi inseriti nel catalogo, non è un incasso effettivo.")
if sold:
    st.caption(f"Valore dei capi segnati come venduti: {money(sold_value)}. È calcolato usando il prezzo salvato nell'annuncio, non un prezzo di vendita confermato.")

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
    st.markdown('<div class="eyebrow">01 / Dettagli del capo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        category = st.selectbox("Categoria *", CATEGORIES)
        brand = st.text_input("Marca", placeholder="Es. Levi's, Zara, Jhavè")
        size = st.text_input("Taglia", placeholder="Es. 48, M, XL")
        color_options = [
            "Nero", "Bianco", "Blu", "Blu navy", "Azzurro", "Grigio", "Grigio antracite",
            "Beige", "Panna", "Marrone", "Verde", "Verde oliva", "Rosso", "Bordeaux",
            "Rosa", "Fucsia", "Viola", "Giallo", "Arancione", "Jeans / denim", "Multicolore", "Fantasia", "Altro"
        ]
        selected_colors = st.multiselect(
            "Colore (puoi scegliere più opzioni)",
            color_options,
            help="Seleziona uno o più colori realmente presenti sul capo."
        )
        custom_color = st.text_input("Colore personalizzato (facoltativo)", placeholder="Es. blu notte, tortora")
        color_parts = list(selected_colors)
        if clean(custom_color):
            color_parts.append(clean(custom_color))
        color = ", ".join(dict.fromkeys(color_parts))
        condition = st.selectbox("Condizioni", CONDITIONS)
        fit_options_by_category = {
            "Jeans": ["Slim Fit", "Skinny", "Regular Fit", "Straight", "Relaxed", "Wide Leg", "Tapered"],
            "Pantaloni": ["Slim Fit", "Regular Fit", "Straight", "Relaxed", "Wide Leg", "Tapered", "Sartoriale"],
            "T-shirt": ["Regular Fit", "Slim Fit", "Oversize", "Relaxed", "Boxy"],
            "Camicia": ["Slim Fit", "Regular Fit", "Relaxed", "Oversize"],
            "Felpa": ["Regular Fit", "Oversize", "Relaxed", "Slim Fit"],
            "Giacca": ["Slim Fit", "Regular Fit", "Relaxed", "Oversize"],
            "Cappotto": ["Regular Fit", "Slim Fit", "Oversize", "Relaxed"],
            "Abito": ["Slim Fit", "Regular Fit", "Sartoriale"],
        }
        fit_options = fit_options_by_category.get(category, ["Regular Fit", "Slim Fit", "Relaxed", "Oversize"])
        selected_fits = st.multiselect("Vestibilità (selezione multipla)", fit_options)
        custom_fit = st.text_input("Vestibilità personalizzata (facoltativo)", placeholder="Es. cropped, tapered")
        fit_parts = list(selected_fits)
        if clean(custom_fit):
            fit_parts.append(clean(custom_fit))
        fit = ", ".join(dict.fromkeys(fit_parts))
        style_options = ["Sartoriale", "Elegante", "Casual", "Casual chic", "Sportivo", "Streetwear", "Minimal", "Vintage", "Classico", "Cerimonia", "Business"]
        selected_styles = st.multiselect("Stile (selezione multipla)", style_options)
        custom_style = st.text_input("Altro stile (facoltativo)", placeholder="Es. old money, smart casual")
        style_parts = list(selected_styles)
        if clean(custom_style):
            style_parts.append(clean(custom_style))
        style = ", ".join(dict.fromkeys(style_parts))
    with c2:
        price = st.number_input("Prezzo richiesto (€)", min_value=0.0, max_value=100000.0, value=39.99, step=1.0)
        cost = st.number_input("Costo per te (€) — facoltativo", min_value=0.0, max_value=100000.0, value=0.0, step=1.0)
        material_options = [
            "Cotone", "Poliestere", "Elastan", "Lana", "Lino", "Seta",
            "Viscosa", "Acrilico", "Nylon / Poliammide", "Denim", "Pelle",
            "Pelle sintetica", "Camoscio", "Cashmere", "Modal", "Lyocell",
            "Canapa", "Bambù", "Raso", "Velluto", "Tulle", "Piumino / Piuma",
            "Materiale riciclato", "Altro"
        ]
        selected_materials = st.multiselect(
            "Materiale (puoi scegliere più opzioni)",
            material_options,
            help="Seleziona tutti i materiali indicati sull'etichetta del capo."
        )
        custom_material = st.text_input(
            "Composizione o dettagli aggiuntivi (facoltativo)",
            placeholder="Es. 97% cotone, 3% elastan"
        )
        material_parts = list(selected_materials)
        if clean(custom_material):
            material_parts.append(clean(custom_material))
        material = ", ".join(dict.fromkeys(material_parts))
        tone = st.selectbox("Tono dell'annuncio", ["Naturale", "Essenziale", "Elegante"])
        platform = st.selectbox("Piattaforma di destinazione", ["Generico", "Vinted", "eBay", "Subito", "Facebook Marketplace"])
    keyword_map = {
        "Jeans": ["denim", "cinque tasche", "casual", "streetwear", "jeans uomo", "jeans donna", "slim fit", "regular fit", "straight"],
        "Pantaloni": ["sartoriale", "elegante", "casual chic", "ufficio", "chino", "pantaloni uomo", "pantaloni donna", "slim fit", "regular fit"],
        "T-shirt": ["basic", "casual", "cotone", "streetwear", "t-shirt uomo", "t-shirt donna", "oversize", "girocollo"],
        "Camicia": ["elegante", "formale", "ufficio", "sartoriale", "casual chic", "camicia uomo", "camicia donna", "slim fit"],
        "Felpa": ["casual", "sportivo", "streetwear", "comoda", "oversize", "con cappuccio", "senza cappuccio"],
        "Giacca": ["elegante", "casual", "outerwear", "ufficio", "blazer", "capospalla"],
        "Cappotto": ["elegante", "invernale", "capospalla", "classico", "caldo"],
        "Scarpe": ["sneakers", "elegante", "casual", "streetwear", "comfort", "calzature"],
        "Abito": ["elegante", "cerimonia", "formale", "ufficio", "sartoriale", "look raffinato"],
        "Borsa": ["accessorio", "quotidiano", "elegante", "casual", "capiente"],
        "Accessori": ["accessorio moda", "look", "elegante", "casual", "unisex"],
        "Altro": ["abbigliamento", "moda", "casual", "elegante", "outfit"]
    }
    color_keyword_map = {
        "Nero": ["nero", "total black"], "Bianco": ["bianco", "total white"],
        "Blu": ["blu", "blu classico"], "Blu navy": ["blu navy", "blu scuro", "navy"],
        "Azzurro": ["azzurro", "blu chiaro"], "Grigio": ["grigio"], "Grigio antracite": ["antracite", "grigio scuro"],
        "Beige": ["beige", "neutro"], "Panna": ["panna", "avorio"], "Marrone": ["marrone", "terra"],
        "Verde": ["verde"], "Verde oliva": ["verde oliva", "militare"], "Rosso": ["rosso"],
        "Bordeaux": ["bordeaux", "rosso scuro"], "Rosa": ["rosa"], "Fucsia": ["fucsia"],
        "Viola": ["viola"], "Giallo": ["giallo"], "Arancione": ["arancione"],
        "Jeans / denim": ["denim", "effetto jeans"], "Multicolore": ["multicolore"],
        "Fantasia": ["fantasia", "pattern"]
    }
    suggested_keywords = list(keyword_map.get(category, keyword_map["Altro"]))
    for selected_color in selected_colors:
        suggested_keywords.extend(color_keyword_map.get(selected_color, [selected_color.lower()]))
    if material:
        suggested_keywords.extend([part.strip().lower() for part in material.split(",") if part.strip()])
    if fit:
        suggested_keywords.extend([part.strip().lower() for part in fit.split(",") if part.strip()])
    if style:
        suggested_keywords.extend([part.strip().lower() for part in style.split(",") if part.strip()])
    suggested_keywords = list(dict.fromkeys(suggested_keywords))
    selected_keywords = st.multiselect(
        "Parole chiave suggerite (selezione multipla)",
        suggested_keywords,
        help="I suggerimenti cambiano in base alla categoria, ai colori e ai materiali selezionati."
    )
    custom_keywords = st.text_input("Altre parole chiave (facoltativo)", placeholder="Es. made in Italy, slim fit")
    keyword_parts = list(selected_keywords)
    if clean(custom_keywords):
        keyword_parts.extend([part.strip() for part in custom_keywords.split(",") if part.strip()])
    keywords = ", ".join(dict.fromkeys(keyword_parts))
    details = st.text_area("Dettagli da valorizzare", placeholder="Vestibilità, misure, modello, particolari o eventuali difetti da segnalare…", height=110)
    submitted = st.button("✦ Genera la bozza", type="primary", use_container_width=True)
    if submitted:
        item = {"category":category, "brand":clean(brand), "size":clean(size), "color":clean(color), "condition":condition, "price":float(price), "cost":float(cost), "material":clean(material), "fit":clean(fit), "style":clean(style), "platform":platform, "details":clean(details), "tone":tone, "keywords":clean(keywords), "created":datetime.now().strftime("%Y-%m-%d %H:%M")}
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
                        "platform": item.get("platform", "Generico"),
                        "status": "Da pubblicare",
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
    items = st.session_state["items"]
    if not items:
        st.info("Il catalogo è vuoto. Crea un annuncio e scegli «Salva nel catalogo» per iniziare. Gli annunci salvati resteranno nel tuo account.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Annunci salvati", len(items))
        m2.metric("Valore richiesto totale", money(sum(float(x.get("price", 0)) for x in items)))

        # Ricerca e filtri del catalogo
        status_col, filter_col1, filter_col2 = st.columns([1, 2, 1])
        with status_col:
            catalog_status = st.selectbox("Stato", ["Tutti gli stati", "Da pubblicare", "Pubblicato", "Venduto"], key="catalog_status")
        with filter_col1:
            catalog_query = st.text_input("🔎 Cerca nel catalogo", placeholder="Titolo, marca, colore o taglia…", key="catalog_query")
        with filter_col2:
            available_categories = ["Tutte le categorie"] + sorted({str(x.get("category") or "Altro") for x in items})
            catalog_category = st.selectbox("Categoria", available_categories, key="catalog_category")
        filtered_items = [
            x for x in items
            if (not catalog_query.strip() or catalog_query.strip().lower() in " ".join(str(x.get(k, "")) for k in ("title", "brand", "category", "color", "size", "description")).lower())
            and (catalog_category == "Tutte le categorie" or str(x.get("category") or "Altro") == catalog_category)
            and (catalog_status == "Tutti gli stati" or str(x.get("status") or "Da pubblicare") == catalog_status)
        ]
        st.caption(f"Visualizzati {len(filtered_items)} di {len(items)} annunci.")
        rows = [{"Titolo":x.get("title",""), "Stato":x.get("status","Da pubblicare"), "Categoria":x.get("category",""), "Taglia":x.get("size",""), "Colore":x.get("color",""), "Prezzo":float(x.get("price",0)), "Condizioni":x.get("condition","")} for x in filtered_items]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            export_rows = [{
                "Titolo": x.get("title", ""),
                "Descrizione": x.get("description", ""),
                "Hashtag": x.get("hashtags", ""),
                "Stato": x.get("status", "Da pubblicare"),
                "Categoria": x.get("category", ""),
                "Marca": x.get("brand", ""),
                "Taglia": x.get("size", ""),
                "Colore": x.get("color", ""),
                "Condizioni": x.get("condition", ""),
                "Materiale": x.get("material", ""),
                "Dettagli aggiuntivi": x.get("details", ""),
                "Piattaforma": x.get("platform", ""),
                "Prezzo richiesto": float(x.get("price", 0) or 0),
            } for x in filtered_items]
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=list(export_rows[0].keys()))
            writer.writeheader()
            writer.writerows(export_rows)
            st.download_button("↓ Esporta catalogo completo CSV", csv_buffer.getvalue().encode("utf-8-sig"), "catalogo_listingai.csv", "text/csv", use_container_width=True, help="Include descrizioni, hashtag e tutti i dettagli salvati per gli articoli visualizzati.")
        else:
            st.info("Nessun annuncio corrisponde alla ricerca. Prova a cambiare parole o categoria.")

        st.markdown("---")
        st.markdown("---")
        st.markdown('<div class="section-title">Duplica o elimina un annuncio</div><div class="section-subtitle">Riutilizza i dettagli di un capo simile oppure rimuovi un articolo che non ti serve più.</div>', unsafe_allow_html=True)
        managed_items = [x for x in filtered_items if x.get("id")]
        if managed_items:
            manage_options = {
                f"{x.get('title') or 'Articolo senza titolo'} · {money(x.get('price',0))} · ID {str(x.get('id'))[-6:]}": x
                for x in managed_items
            }
            manage_label = st.selectbox("Scegli l'articolo", list(manage_options.keys()), key="catalog_manage_choice")
            managed = manage_options[manage_label]
            duplicate_col, delete_col = st.columns(2)
            with duplicate_col:
                st.markdown("**Crea una copia**")
                st.caption("Crea un nuovo annuncio in bozza con i dettagli dell'articolo selezionato.")
                if st.button("Duplica annuncio", use_container_width=True, key="catalog_duplicate_button"):
                    try:
                        copy_fields = ("title", "description", "hashtags", "category", "brand", "size", "color", "condition", "material", "details", "platform", "price")
                        duplicate_data = {field: managed.get(field) for field in copy_fields}
                        duplicate_data["title"] = (str(managed.get("title") or "Articolo") + " (copia)")[:100]
                        duplicate_data["status"] = "Da pubblicare"
                        duplicate_data["user_id"] = st.session_state.auth_user_id
                        supabase.table("listings").insert(duplicate_data).execute()
                        st.session_state.db_loaded_for = ""
                        st.success("Copia creata. Puoi modificarla nella sezione qui sopra.")
                        st.rerun()
                    except Exception as e:
                        st.error("Duplicazione non riuscita. Dettaglio: " + str(e))
            with delete_col:
                st.markdown("**Elimina definitivamente**")
                st.caption("L'eliminazione non può essere annullata.")
                confirm_delete = st.checkbox("Confermo di voler eliminare questo annuncio", key="catalog_confirm_delete")
                if st.button("Elimina annuncio", type="secondary", use_container_width=True, disabled=not confirm_delete, key="catalog_delete_button"):
                    try:
                        supabase.table("listings").delete().eq("id", managed["id"]).eq("user_id", st.session_state.auth_user_id).execute()
                        st.session_state.db_loaded_for = ""
                        st.session_state.pop("catalog_confirm_delete", None)
                        st.success("Annuncio eliminato.")
                        st.rerun()
                    except Exception as e:
                        st.error("Eliminazione non riuscita. Dettaglio: " + str(e))
        else:
            st.caption("Nessun annuncio disponibile per queste operazioni con i filtri attuali.")

        st.markdown('<div class="section-title">Modifica un annuncio</div><div class="section-subtitle">Aggiorna titolo, descrizione, hashtag e prezzo senza ricreare il prodotto.</div>', unsafe_allow_html=True)
        editable_items = [x for x in filtered_items if x.get("id")]
        if editable_items:
            st.info("Per modificare un articolo: selezionalo qui sotto, cambia i campi nel modulo e premi «Salva tutte le modifiche». La tabella sopra serve solo per consultare gli articoli.")
            edit_options = {
                f"{x.get('title') or 'Articolo senza titolo'} · {money(x.get('price',0))} · ID {str(x.get('id'))[-6:]}": x
                for x in editable_items
            }
            edit_label = st.selectbox("1. Scegli l'articolo da modificare", list(edit_options.keys()), key="catalog_edit_choice")
            chosen = edit_options[edit_label]
            st.markdown('<div class="info-card" style="margin-bottom:12px"><b>Modifica tutti i dettagli</b><p class="small-muted">Aggiorna i dati del capo e salva: il record esistente viene aggiornato, senza crearne uno nuovo.</p></div>', unsafe_allow_html=True)
            with st.form("edit_catalog_listing_form"):
                edited_title = st.text_input("Titolo annuncio", value=chosen.get("title", ""), max_chars=100)
                edited_description = st.text_area("Descrizione", value=chosen.get("description", ""), height=170)
                edited_hashtags = st.text_input("Hashtag", value=chosen.get("hashtags", ""))
                ec1, ec2 = st.columns(2)
                with ec1:
                    edited_category = st.selectbox("Categoria", CATEGORIES, index=CATEGORIES.index(chosen.get("category")) if chosen.get("category") in CATEGORIES else 0)
                    edited_brand = st.text_input("Marca", value=str(chosen.get("brand") or ""))
                    edited_size = st.text_input("Taglia", value=str(chosen.get("size") or ""))
                    edited_color = st.text_input("Colore", value=str(chosen.get("color") or ""))
                    edited_condition = st.selectbox("Condizioni", CONDITIONS, index=CONDITIONS.index(chosen.get("condition")) if chosen.get("condition") in CONDITIONS else 0)
                with ec2:
                    edited_material = st.text_input("Materiale / composizione", value=str(chosen.get("material") or ""))
                    edited_platform = st.selectbox("Piattaforma", ["Generico", "Vinted", "eBay", "Subito", "Facebook Marketplace"], index=["Generico", "Vinted", "eBay", "Subito", "Facebook Marketplace"].index(chosen.get("platform")) if chosen.get("platform") in ["Generico", "Vinted", "eBay", "Subito", "Facebook Marketplace"] else 0)
                    edited_price = st.number_input("Prezzo richiesto (€)", min_value=0.0, max_value=100000.0, value=float(chosen.get("price") or 0), step=1.0)
                    status_options = ["Da pubblicare", "Pubblicato", "Venduto"]
                    current_status = chosen.get("status", "Da pubblicare")
                    edited_status = st.selectbox("Stato annuncio", status_options, index=status_options.index(current_status) if current_status in status_options else 0)
                edited_details = st.text_area("Dettagli aggiuntivi", value=str(chosen.get("details") or ""), height=100, help="Vestibilità, misure, particolari o difetti da segnalare.")
                save_edit = st.form_submit_button("Salva tutte le modifiche", type="primary", use_container_width=True)
            if save_edit:
                if not edited_title.strip():
                    st.error("Il titolo non può essere vuoto.")
                else:
                    try:
                        supabase.table("listings").update({
                            "title": edited_title.strip(),
                            "description": edited_description.strip(),
                            "hashtags": edited_hashtags.strip(),
                            "category": edited_category,
                            "brand": edited_brand.strip(),
                            "size": edited_size.strip(),
                            "color": edited_color.strip(),
                            "condition": edited_condition,
                            "material": edited_material.strip(),
                            "details": edited_details.strip(),
                            "platform": edited_platform,
                            "price": float(edited_price),
                            "status": edited_status,
                        }).eq("id", chosen["id"]).eq("user_id", st.session_state.auth_user_id).execute()
                        st.session_state.db_loaded_for = ""
                        st.success("Annuncio aggiornato correttamente.")
                        st.rerun()
                    except Exception as e:
                        st.error("Modifica non riuscita. Dettaglio: " + str(e))
        else:
            st.caption("Nessun annuncio salvato disponibile per la modifica con questi filtri.")



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
        a1.metric("I tuoi annunci salvati", len(st.session_state["items"]))
        a2.metric("Valore del tuo catalogo", money(sum(float(x.get("price", 0)) for x in st.session_state["items"])))
        a3.metric("Stato database", "Connesso", help="La lettura del catalogo è riuscita in questa sessione.")
        st.markdown('<div class="info-card"><div class="eyebrow">GESTIONE PRODOTTO</div><p style="margin-top:10px"><b>Prossimi moduli amministrativi</b></p><p class="small-muted">Questa prima area admin verifica il tuo ruolo e mostra lo stato del tuo catalogo. Gestione utenti, piani, pagamenti e statistiche globali richiederanno endpoint e autorizzazioni server-side dedicati: non vengono abilitati con una semplice verifica email.</p></div>', unsafe_allow_html=True)
        st.caption("Email amministratore configurata: " + admin_email)

st.markdown("---")
st.markdown('<div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><span class="small-muted"><b>ListingAI</b> · Seller studio</span><span class="small-muted">Prototipo in sviluppo · Non affiliato ufficialmente a Vinted o altri marketplace</span></div>', unsafe_allow_html=True)
