import os
import sqlite3
import hmac
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

# The service-role key bypasses Supabase RLS, so protect every section that can
# read or mutate shared data, not just the cycle-history page.
try:
    _service_key_configured = bool(str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip())
    _app_password = str(st.secrets.get("CICCIO_APP_PASSWORD", "")).strip()
except Exception:
    _service_key_configured = False
    _app_password = ""

if _service_key_configured:
    if not _app_password:
        st.error("Accesso bloccato: configura CICCIO_APP_PASSWORD nei Secrets prima di usare la chiave service-role.")
        st.stop()
    _entered_password = st.sidebar.text_input("Password di accesso a Ciccio", type="password", key="global_ciccio_password")
    if not _entered_password or not hmac.compare_digest(_entered_password.encode("utf-8"), _app_password.encode("utf-8")):
        st.info("Inserisci la password per accedere ai dati personali di Ciccio.")
        st.stop()

st.title("🧠 Ciccio")
st.caption("Agente personale orientato a creare valore, ridurre i costi e imparare dal lavoro svolto.")
with st.sidebar:
    st.header("Missione")
    st.write("Generare opportunità concrete con budget iniziale minimo.")
    st.info("I cicli programmati possono continuare tramite GitHub Actions anche con questa app chiusa. Ciccio può modificare solo le risorse per cui dispone di strumenti e permessi; le modifiche al codice devono essere testate e reversibili. Spese, pubblicazioni e contatti esterni richiedono approvazione.")
    section = st.radio("Area", ["Conversazione", "Memoria", "Attività", "Cicli automatici", "Registro economico"])

if section == "Conversazione":
    st.subheader("Parla con Ciccio")
    st.write("Raccontami un obiettivo o un problema. Ciccio può organizzare le idee e trasformarle in azioni.")

    # Stato operativo in chat: dati registrati dal runner, non supposizioni del modello.
    with st.expander("📡 Cosa sta facendo Ciccio nei cicli automatici", expanded=True):
        if st.button("Aggiorna stato", key="refresh_ciccio_status"):
            st.rerun()
        status_url = st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
        status_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") if hasattr(st, "secrets") else ""
        if status_url and status_key:
            try:
                from supabase import create_client
                status_sb = create_client(status_url, status_key)
                status_runs = (status_sb.table("ciccio_agent_runs").select(
                    "created_at,goal,action,status,result,verification"
                ).order("created_at", desc=True).limit(5).execute().data or [])
                if not status_runs:
                    st.info("Non ci sono ancora cicli registrati in Supabase.")
                for item in status_runs:
                    when = str(item.get("created_at", ""))[:16].replace("T", " ")
                    with st.container(border=True):
                        st.markdown(f"**{when} · {item.get('status', 'sconosciuto')}**")
                        st.write(item.get("goal", "Obiettivo non registrato"))
                        st.caption("Azione: " + str(item.get("action", "Non specificata"))[:500])
                        result_text = str(item.get("result", "") or "").strip()
                        if result_text:
                            st.write(result_text[:1800])
                        else:
                            st.caption("Nessun risultato dettagliato salvato.")
                        if item.get("verification"):
                            st.caption("Verifica prevista: " + str(item["verification"])[:500])
                st.caption("Il completamento tecnico non dimostra che l'opportunità sia redditizia o abbia generato incassi.")
            except Exception as status_error:
                st.warning("Non riesco a leggere ora il registro dei cicli da Supabase.")
                st.caption(str(status_error)[:180])
        else:
            st.info("Per vedere i cicli qui, configura SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nei Secrets di Streamlit.")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for role, msg in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(msg)
    prompt = st.chat_input("Scrivi a Ciccio…")
    if prompt:
        st.session_state.chat.append(("user", prompt))
        low = prompt.lower()
        api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        if api_key:
            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                # Memoria condivisa e persistente: Supabase prima, SQLite come fallback.
                memory_context = ""
                sb = None
                supabase_url = st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
                supabase_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") if hasattr(st, "secrets") else ""
                ciccio_owner_id = str(st.secrets.get("CICCIO_USER_ID", "")).strip() if hasattr(st, "secrets") else ""
                if supabase_url and supabase_key and ciccio_owner_id:
                    try:
                        from supabase import create_client
                        sb = create_client(supabase_url, supabase_key)
                        memory_rows = (sb.table("ciccio_memories").select(
                            "created_at,kind,content"
                        ).eq("user_id", ciccio_owner_id).order("created_at", desc=True).limit(25).execute().data or [])
                        task_rows = (sb.table("ciccio_tasks").select(
                            "title,status,notes"
                        ).eq("user_id", ciccio_owner_id).neq("status", "Completata").limit(15).execute().data or [])
                        memory_context = "\\n".join(
                            f"- [{str(x.get('created_at',''))[:16]}] {x.get('kind','Nota')}: {str(x.get('content',''))[:500]}"
                            for x in reversed(memory_rows)
                        )
                        memory_context += "\\nATTIVITÀ APERTE:\\n" + "\\n".join(
                            f"- {x.get('title','')} ({x.get('status','Da fare')}): {x.get('notes','')}"
                            for x in task_rows
                        )
                    except Exception:
                        sb = None
                if not memory_context:
                    memory_rows = conn.execute(
                        "SELECT created_at,kind,content FROM memories "
                        "WHERE kind NOT LIKE 'finanza:%' ORDER BY id DESC LIMIT 20"
                    ).fetchall()
                    memory_context = "\\n".join(
                        f"- [{created[:16]}] {kind}: {content[:500]}"
                        for created, kind, content in reversed(memory_rows)
                    )
                run_context = "(registro dei cicli non disponibile)"
                if sb is not None:
                    try:
                        recent_runs = (sb.table("ciccio_agent_runs").select(
                            "created_at,goal,action,status,result"
                        ).order("created_at", desc=True).limit(5).execute().data or [])
                        run_context = "\\n".join(
                            f"- {str(item.get('created_at',''))[:16]} | stato={item.get('status','?')} | "
                            f"obiettivo={item.get('goal','')} | azione={item.get('action','')} | "
                            f"esito={str(item.get('result',''))[:700]}"
                            for item in recent_runs
                        ) or "(nessun ciclo automatico registrato)"
                    except Exception:
                        run_context = "(registro dei cicli non leggibile ora)"
                system_prompt = (
                    "Sei Ciccio: parla come una persona naturale, presente, diretta e collaborativa, "
                    "non come un modulo automatico o un manuale. Puoi fare domande pertinenti, esprimere "
                    "ragionamenti e proporre iniziative. Mantieni una personalità coerente e ricorda il "
                    "contesto tra sessioni usando la memoria. Se l'utente ha già dato un'informazione, "
                    "non chiedergliela di nuovo. Quando individui un passo utile, proponilo chiaramente "
                    "e spiega perché; non aspettare sempre che l'utente suggerisca ogni dettaglio. "
                    "Aiuta a creare valore e opportunità con budget minimo, privilegiando azioni concrete, "
                    "testabili e legali. L'utente gestisce ListingAI e il marchio Jhavè. "
                    "Distingui ciò che sai da ciò che ipotizzi. Non promettere guadagni e non dichiarare "
                    "di aver compiuto azioni che hai solo proposto. Non dire di lavorare in background "
                    "se non è vero. Prima di contattare persone, pubblicare, spendere denaro o compiere "
                    "azioni esterne, chiedi approvazione. Rispondi in italiano in modo umano e naturale, "
                    "con dettagli proporzionati alla domanda e un prossimo passo utile quando serve."
                    "\\n\\nMEMORIA E CONTESTO PERSISTENTE:\\n"
                    + (memory_context if memory_context else "(nessuna memoria salvata)")
                    + "\\n\\nREGISTRO DEI CICLI AUTOMATICI (dati salvati; non inventare azioni ulteriori):\\n"
                    + run_context
                )
                history = [{"role": "system", "content": system_prompt}]
                for role, msg in st.session_state.chat[-12:]:
                    history.append({"role": "assistant" if role == "assistant" else "user", "content": msg})
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=history,
                    temperature=0.5,
                    max_completion_tokens=700,
                )
                answer = response.choices[0].message.content or "Non sono riuscito a generare una risposta."
            except Exception as e:
                answer = ("Non riesco a contattare Groq. Controlla che GROQ_API_KEY sia configurata "
                          "nei Secrets di Streamlit e che il piano gratuito abbia quota disponibile. "
                          "Dettaglio: " + str(e)[:250])
        else:
            answer = (
                "La modalità AI non è ancora attivata: manca GROQ_API_KEY nei Secrets di Streamlit.\n\n"
                "Crea una chiave gratuita su https://console.groq.com/keys e aggiungila ai Secrets. "
                "Non inserirla mai nel codice GitHub e non attivare un piano a pagamento."
            )
        st.session_state.chat.append(("assistant", answer))
        with st.chat_message("assistant"):
            st.markdown(answer)
        now = datetime.now().isoformat(timespec="seconds")
        # Salva conversazione nella memoria persistente condivisa.
        saved_remote = False
        if 'sb' in locals() and sb is not None and locals().get("ciccio_owner_id"):
            try:
                sb.table("ciccio_memories").insert([
                    {"user_id": ciccio_owner_id, "kind": "conversazione", "content": "Utente: " + prompt[:4000]},
                    {"user_id": ciccio_owner_id, "kind": "risposta_assistente", "content": answer[:4000]}
                ]).execute()
                saved_remote = True
            except Exception:
                pass
        if not saved_remote:
            conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)",
                         (now, "conversazione", "Utente: " + prompt))
            conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)",
                         (now, "risposta_assistente", answer[:4000]))
            conn.commit()

elif section == "Memoria":
    st.subheader("Memoria condivisa dell'agente")
    st.caption("La memoria usa la stessa tabella Supabase dei cicli automatici; SQLite resta come ripiego.")
    sb_ui = None
    memory_owner_id = st.secrets.get("CICCIO_USER_ID", "").strip() if hasattr(st, "secrets") else ""
    try:
        u = st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
        k = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") if hasattr(st, "secrets") else ""
        if u and k:
            from supabase import create_client
            sb_ui = create_client(u, k)
    except Exception:
        sb_ui = None
    if sb_ui and not memory_owner_id:
        st.warning("Manca CICCIO_USER_ID nei Secrets di Streamlit: le memorie non possono essere condivise con l’agente in sicurezza.")
    with st.form("memory_form", clear_on_submit=True):
        kind = st.selectbox("Tipo", ["Decisione", "Preferenza", "Idea", "Risultato", "Nota"])
        content = st.text_area("Contenuto", placeholder="Scrivi una nota utile per il progetto…")
        submitted = st.form_submit_button("Salva memoria")
    if submitted and content.strip():
        try:
            if sb_ui:
                if not memory_owner_id:
                    st.error("Configura CICCIO_USER_ID nei Secrets di Streamlit prima di salvare memorie condivise.")
                    st.stop()
                sb_ui.table("ciccio_memories").insert({"user_id": memory_owner_id, "kind": kind, "content": content.strip()}).execute()
            else:
                conn.execute("INSERT INTO memories(created_at,kind,content) VALUES(?,?,?)", (datetime.now().isoformat(timespec="seconds"), kind, content.strip()))
                conn.commit()
            st.success("Memoria salvata.")
            st.rerun()
        except Exception as e:
            st.error("Non sono riuscito a salvare la memoria condivisa.")
            st.caption(str(e)[:200])
    try:
        if sb_ui:
            rows = sb_ui.table("ciccio_memories").select("id,created_at,kind,content").eq("user_id", memory_owner_id).order("created_at", desc=True).limit(100).execute().data or []
        else:
            rows = [{"id": rid, "created_at": created, "kind": k, "content": body} for rid, created, k, body in conn.execute("SELECT id,created_at,kind,content FROM memories WHERE kind NOT LIKE 'finanza:%' ORDER BY id DESC LIMIT 100").fetchall()]
        for item in rows:
            rid, created, k, body = item["id"], str(item.get("created_at", "")), item.get("kind", "Nota"), item.get("content", "")
            with st.expander(f"{k} · {created[:16]}"):
                st.write(body)
                if st.button("Elimina", key=f"delmem{rid}"):
                    if sb_ui:
                        sb_ui.table("ciccio_memories").delete().eq("id", rid).eq("user_id", memory_owner_id).execute()
                    else:
                        conn.execute("DELETE FROM memories WHERE id=?", (rid,))
                        conn.commit()
                    st.rerun()
    except Exception as e:
        st.error("Errore nella lettura della memoria.")
        st.caption(str(e)[:200])

elif section == "Attività":
    st.subheader("Piano operativo condiviso")
    st.caption("Le attività qui sono condivise con i cicli automatici di Ciccio.")
    sb_tasks = None
    task_owner_id = st.secrets.get("CICCIO_USER_ID", "").strip() if hasattr(st, "secrets") else ""
    try:
        u = st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
        k = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") if hasattr(st, "secrets") else ""
        if u and k:
            from supabase import create_client
            sb_tasks = create_client(u, k)
    except Exception:
        sb_tasks = None
    if sb_tasks and not task_owner_id:
        st.warning("Manca CICCIO_USER_ID nei Secrets di Streamlit: le attività condivise con l'agente non possono essere caricate o modificate in sicurezza.")
    with st.form("task_form", clear_on_submit=True):
        title = st.text_input("Nuova attività", placeholder="Es. Preparare un'offerta per 10 negozi")
        notes = st.text_area("Note (facoltative)")
        add = st.form_submit_button("Aggiungi attività")
    if add and title.strip():
        try:
            if sb_tasks:
                if not task_owner_id:
                    st.error("Configura CICCIO_USER_ID nei Secrets di Streamlit prima di aggiungere attività condivise.")
                    st.stop()
                sb_tasks.table("ciccio_tasks").insert({"user_id": task_owner_id, "title": title.strip(), "notes": notes.strip(), "status": "Da fare"}).execute()
            else:
                conn.execute("INSERT INTO tasks(created_at,title,notes) VALUES(?,?,?)", (datetime.now().isoformat(timespec="seconds"), title.strip(), notes.strip()))
                conn.commit()
            st.success("Attività aggiunta.")
            st.rerun()
        except Exception as e:
            st.error("Non sono riuscito a salvare l'attività.")
            st.caption(str(e)[:200])
    try:
        if sb_tasks:
            tasks = (sb_tasks.table("ciccio_tasks").select("id,title,status,notes").eq("user_id", task_owner_id).order("created_at", desc=True).limit(100).execute().data or []) if task_owner_id else []
        else:
            tasks = [{"id": tid, "title": title, "status": status, "notes": notes} for tid, title, status, notes in conn.execute("SELECT id,title,status,notes FROM tasks ORDER BY id DESC").fetchall()]
        if not tasks:
            st.info("Nessuna attività ancora. Aggiungi il primo passo concreto.")
        for task in tasks:
            tid, title, status, notes = task["id"], task["title"], task.get("status", "Da fare"), task.get("notes", "")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                edited_notes = st.text_area("Note e dettagli", value=notes, key=f"notes{tid}", height=100)
                new_status = st.selectbox("Stato", ["Da fare", "In corso", "Completata", "Bloccata"], index=["Da fare","In corso","Completata","Bloccata"].index(status), key=f"status{tid}")
                a, b = st.columns([3,1])
                if a.button("Salva modifiche", key=f"upd{tid}"):
                    if sb_tasks:
                        if not task_owner_id:
                            st.error("Manca CICCIO_USER_ID: modifica bloccata.")
                            st.stop()
                        sb_tasks.table("ciccio_tasks").update({
                            "status": new_status,
                            "notes": edited_notes.strip(),
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                        }).eq("id", tid).eq("user_id", task_owner_id).execute()
                    else:
                        conn.execute("UPDATE tasks SET status=?, notes=? WHERE id=?", (new_status, edited_notes.strip(), tid))
                        conn.commit()
                    st.rerun()
                if b.button("Elimina", key=f"deltask{tid}"):
                    if sb_tasks:
                        if not task_owner_id:
                            st.error("Manca CICCIO_USER_ID: eliminazione bloccata.")
                            st.stop()
                        sb_tasks.table("ciccio_tasks").delete().eq("id", tid).eq("user_id", task_owner_id).execute()
                    else:
                        conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
                        conn.commit()
                    st.rerun()

    except Exception as e:
        st.error("Errore nel caricamento delle attività.")
        st.caption(str(e)[:200])

elif section == "Cicli automatici":
    st.subheader("Cicli automatici di Ciccio")
    st.caption("Questi dati arrivano da GitHub Actions e Supabase: mostra gli esiti, le attività svolte e i fallimenti registrati. Apri ogni ciclo per leggerne il dettaglio.")
    st.markdown("[Apri GitHub Actions per avviare o controllare un ciclo](https://github.com/TonyxCash/ListingAI/actions/workflows/ciccio-agent.yml)")
    supabase_url = st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
    supabase_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") if hasattr(st, "secrets") else ""
    if not supabase_url or not supabase_key:
        st.warning("Per visualizzare i cicli qui, aggiungi SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nei Secrets di Streamlit. Non inserire mai queste chiavi nel codice GitHub o in chat.")
        st.markdown("[Apri il progetto Supabase](https://supabase.com/dashboard/project/hfwlqkrwiwlthpwuivqg/editor)")
    else:
        # Authentication has already been checked globally before any page is rendered.
        try:
            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            runs = (sb.table("ciccio_agent_runs").select(
                "id,created_at,goal,action,reason,expected_result,verification,status,result,model"
            ).order("created_at", desc=True).limit(50).execute().data or [])
            if not runs:
                st.info("Nessun ciclo registrato ancora.")
            else:
                completed = sum(1 for run in runs if run.get("status") == "completed")
                planned = sum(1 for run in runs if run.get("status") == "planned")
                blocked = sum(1 for run in runs if run.get("status") in ("blocked", "failed"))
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Cicli registrati", len(runs))
                m2.metric("Completati", completed)
                m3.metric("In attesa", planned)
                m4.metric("Bloccati / falliti", blocked)
                for run in runs:
                    created = str(run.get("created_at", ""))[:16].replace("T", " ")
                    with st.expander(f"{created} · {run.get('status', 'sconosciuto')} · {run.get('goal', 'Senza obiettivo')[:90]}"):
                        st.markdown("**Azione eseguita o tentata**")
                        st.write(run.get("action", ""))
                        st.markdown("**Perché**")
                        st.write(run.get("reason", ""))
                        st.markdown("**Risultato atteso**")
                        st.write(run.get("expected_result", ""))
                        st.markdown("**Come verificarla**")
                        st.write(run.get("verification", ""))
                        st.markdown("**Esito registrato**")
                        st.write(run.get("result", "Nessun esito registrato"))
                        st.caption("Modello: " + str(run.get("model", "non indicato")))
                st.caption("Per sicurezza, questa schermata mostra i cicli ma non consente di approvare o eseguire azioni esterne.")
        except Exception as e:
            st.error("Non riesco a leggere i cicli da Supabase. Verifica i Secrets e che la tabella ciccio_agent_runs esista.")
            st.caption(str(e)[:250])

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
st.caption("Ciccio AI · agente in evoluzione · i cicli programmati operano entro strumenti e permessi configurati; verifica le modifiche importanti.")
