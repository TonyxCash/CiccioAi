import os
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = Path(os.getenv("CICCIO_DB_PATH", str(APP_DIR / "ciccio.db")))

st.set_page_config(page_title="Ciccio AI", page_icon="🧠", layout="wide")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        kind TEXT NOT NULL,
        content TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Da fare',
        notes TEXT DEFAULT ''
    )""")
    conn.commit()
    return conn

conn = db()

st.markdown("""
<style>
.stApp {background: linear-gradient(140deg,#071b20 0%,#0c292d 55%,#102b35 100%); color:#f2fbfa}
section[data-testid="stSidebar"] {background:#091f24}
div[data-testid="stMetric"] {background:#12353a;padding:16px;border-radius:14px;border:1px solid #24535a}
.stButton>button {border-radius:10px;border:1px solid #36b7a5}
</style>
""", unsafe_allow_html=True)

st.title("🧠 Ciccio")
st.caption("Agente personale orientato a creare valore, ridurre i costi e imparare dal lavoro svolto.")
with st.sidebar:
    st.header("Missione")
    st.write("Generare opportunità concrete con budget iniziale minimo.")
    st.info("Questa versione è un prototipo: non lavora in background quando l'app è chiusa e non esegue pagamenti o azioni esterne autonomamente.")
    section = st.radio("Area", ["Conversazione", "Memoria", "Attività", "Registro economico"])

if section == "Conversazione":
    st.subheader("Parla con Ciccio")
    st.write("Raccontami un obiettivo o un problema. Ciccio può organizzare le idee e trasformarle in azioni.")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for role, msg in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(msg)
    prompt = st.chat_input("Scrivi a Ciccio…")
    if prompt:
        st.session_state.chat.append(("user", prompt))
        low = prompt.lower()
        if any(w in low for w in ["soldi", "guadagn", "entrate", "cliente", "vendere", "ricavi"]):
            answer = ("**Analisi orientata ai ricavi**\n\n"
                      "1. Cerca un servizio che risolva un problema urgente e per cui qualcuno pagherebbe.\n"
                      "2. Proponi una versione semplice prima di costruire una piattaforma completa.\n"
                      "3. Contatta potenziali clienti e misura le risposte.\n"
                      "4. Registra incassi, costi e margine.\n\n"
                      "**Prossima azione:** scegliamo un cliente specifico e prepariamo un'offerta che puoi inviare oggi. "
                      "Non posso garantire guadagni; verifichiamo ogni ipotesi con dati reali.")
        elif any(w in low for w in ["piano", "priorità", "priorita", "iniziare", "prossimo"]):
            answer = ("**Piano operativo**\n\n"
                      "• Definire il risultato desiderato.\n"
                      "• Scomporlo in un'attività che richieda meno di un'ora.\n"
                      "• Eseguire e registrare l'esito.\n"
                      "• Aggiornare il piano in base ai risultati.\n\n"
                      "Posso pianificare e aiutarti a valutare le opzioni, ma questa versione non esegue lavoro in background.")
        else:
            answer = ("Ho letto il tuo messaggio. Per aiutarti in modo concreto, posso trasformarlo in un piano, "
                      "una lista di attività o una proposta commerciale.\n\n"
                      "**Domanda di Ciccio:** qual è il risultato pratico che vuoi ottenere e quale vincolo è più importante?")
        st.session_state.chat.append(("assistant", answer))
        with st.chat_message("assistant"):
            st.markdown(answer)
        conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), "conversazione", "Utente: " + prompt))
        conn.commit()

elif section == "Memoria":
    st.subheader("Memoria di lavoro")
    st.caption("Salva qui decisioni e informazioni non sensibili da riutilizzare nelle sessioni future.")
    with st.form("memory_form", clear_on_submit=True):
        kind = st.selectbox("Tipo", ["Decisione", "Preferenza", "Idea", "Risultato", "Nota"])
        content = st.text_area("Contenuto", placeholder="Scrivi una nota utile per il progetto…")
        submitted = st.form_submit_button("Salva memoria")
    if submitted and content.strip():
        conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), kind, content.strip()))
        conn.commit()
        st.success("Memoria salvata.")
    rows = conn.execute("SELECT id,created_at,kind,content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    for rid, created, k, c in rows:
        with st.expander(f"{k} · {created[:16]}"):
            st.write(c)
            if st.button("Elimina", key=f"delmem{rid}"):
                conn.execute("DELETE FROM memories WHERE id=?", (rid,))
                conn.commit()
                st.rerun()

elif section == "Attività":
    st.subheader("Piano operativo")
    with st.form("task_form", clear_on_submit=True):
        title = st.text_input("Nuova attività", placeholder="Es. Preparare un'offerta per 10 negozi")
        notes = st.text_area("Note (facoltative)")
        add = st.form_submit_button("Aggiungi attività")
    if add and title.strip():
        conn.execute("INSERT INTO tasks(created_at,title,notes) VALUES(?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), title.strip(), notes.strip()))
        conn.commit()
        st.success("Attività aggiunta.")
    tasks = conn.execute("SELECT id,title,status,notes FROM tasks ORDER BY id DESC").fetchall()
    if not tasks:
        st.info("Nessuna attività ancora. Aggiungi il primo passo concreto.")
    for tid, title, status, notes in tasks:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            if notes:
                st.caption(notes)
            new_status = st.selectbox("Stato", ["Da fare", "In corso", "Completata"], index=["Da fare","In corso","Completata"].index(status), key=f"status{tid}")
            a, b = st.columns([3,1])
            if a.button("Aggiorna stato", key=f"upd{tid}"):
                conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, tid))
                conn.commit()
                st.rerun()
            if b.button("Elimina", key=f"del{tid}"):
                conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
                conn.commit()
                st.rerun()

else:
    st.subheader("Registro economico")
    st.caption("Inserisci dati reali. Il registro non è collegato a conti bancari.")
    with st.form("finance_form", clear_on_submit=True):
        kind = st.selectbox("Movimento", ["Entrata", "Spesa"])
        amount = st.number_input("Importo (€)", min_value=0.0, step=1.0, format="%.2f")
        description = st.text_input("Descrizione")
        save = st.form_submit_button("Registra")
    if save and amount > 0 and description.strip():
        conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), "finanza:" + kind, f"{amount:.2f} EUR — {description.strip()}"))
        conn.commit()
        st.success("Movimento registrato.")
    entries = conn.execute("SELECT kind,content FROM memories WHERE kind LIKE 'finanza:%' ORDER BY id DESC").fetchall()
    income = sum(float(c.split(" EUR")[0]) for k,c in entries if k == "finanza:Entrata")
    expenses = sum(float(c.split(" EUR")[0]) for k,c in entries if k == "finanza:Spesa")
    c1,c2,c3 = st.columns(3)
    c1.metric("Entrate", f"€ {income:.2f}")
    c2.metric("Spese", f"€ {expenses:.2f}")
    c3.metric("Saldo registrato", f"€ {income-expenses:.2f}")
    for k,c in entries:
        st.write(f"**{k.split(':',1)[1]}** · {c}")

st.divider()
st.caption("Ciccio AI · prototipo iniziale · verifica sempre i risultati prima di prendere decisioni economiche.")
