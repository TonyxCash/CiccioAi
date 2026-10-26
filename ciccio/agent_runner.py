"""Ciccio autonomous agent cycle.
Autonomy is currently bounded to safe actions inside its own Supabase workspace:
create/update tasks and save durable memories. External actions require approval.
"""
import json
import os
import smtplib
import time
from email.message import EmailMessage
from datetime import datetime, timezone

from groq import Groq
from supabase import create_client

MODEL = "openai/gpt-oss-20b"


def groq_completion_with_retry(groq, *, attempts=3, **kwargs):
    """Retry only transient Groq/API transport failures; never repeat database actions."""
    for attempt in range(attempts):
        try:
            return groq.chat.completions.create(**kwargs)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            name = type(exc).__name__.lower()
            transient = (
                status == 429
                or (isinstance(status, int) and status >= 500)
                or any(token in name for token in ("timeout", "connection", "temporarilyunavailable"))
            )
            if not transient or attempt >= attempts - 1:
                raise
            delay = min(2 ** attempt, 4)
            print(f"Errore temporaneo Groq ({type(exc).__name__}); nuovo tentativo tra {delay}s ({attempt + 2}/{attempts}).")
            time.sleep(delay)


def notify_email(subject, message):
    """Send Ciccio's cycle summary by email when SMTP secrets are configured."""
    import re
    import unicodedata
    from email.policy import SMTP

    def clean(value):
        value = unicodedata.normalize("NFKC", str(value or ""))
        # NBSP often enters GitHub Secrets through copy/paste; remove it explicitly.
        value = value.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2007", " ")
        value = "".join(
            " " if ch.isspace() or unicodedata.category(ch).startswith("Z") else ch
            for ch in value
        )
        return re.sub(r" +", " ", value).strip()

    def ascii_setting(label, value):
        value = clean(value)
        try:
            value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"{label} contiene caratteri non ASCII alla posizione {exc.start}; "
                "correggi il secret GitHub Actions."
            ) from None
        return value

    stage = "lettura configurazione"
    try:
        host = ascii_setting("SMTP_HOST", os.getenv("SMTP_HOST", "smtp.gmail.com"))
        port = int(clean(os.getenv("SMTP_PORT", "587")))
        username = ascii_setting("SMTP_USERNAME", os.getenv("SMTP_USERNAME", ""))
        password = ascii_setting("SMTP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
        recipient = ascii_setting("EMAIL_TO", os.getenv("EMAIL_TO", ""))
        sender = ascii_setting("EMAIL_FROM", os.getenv("EMAIL_FROM", "")) or username
        if not all((host, username, password, recipient, sender)):
            print("Email SMTP non configurata: ciclo salvato senza invio email.")
            return False

        stage = "costruzione messaggio"
        email = EmailMessage(policy=SMTP)
        safe_subject = clean(subject).encode("ascii", "backslashreplace").decode("ascii")[:180]
        email["Subject"] = safe_subject
        email["From"] = sender
        email["To"] = recipient
        # Normalize all body whitespace before MIME encoding; never pass NBSP onward.
        body = clean(message)
        body = body.encode("ascii", "backslashreplace").decode("ascii")
        email.set_content(body[:12000], charset="utf-8", cte="quoted-printable")

        stage = "connessione SMTP"
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            stage = "autenticazione SMTP"
            server.login(username, password)
            stage = "invio messaggio SMTP"
            server.send_message(email, from_addr=sender, to_addrs=[recipient])
        print("Email Ciccio inviata al destinatario configurato.")
        return True
    except Exception as exc:
        detail = str(exc).encode("ascii", "backslashreplace").decode("ascii")
        print(f"Invio email non riuscito durante {stage} ({type(exc).__name__}): {detail}")
        return False
def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def rows(db, table, columns, limit, order="created_at", user_id=None):
    query = db.table(table).select(columns)
    if user_id and table in {"ciccio_memories", "ciccio_tasks"}:
        query = query.eq("user_id", user_id)
    return query.order(order, desc=True).limit(limit).execute().data or []


def ask_agent(groq, memories, tasks, previous):
    system = """
Sei Ciccio, agente persistente con obiettivo stabile: lavorare in cicli di memoria,
ragionamento, decisione, azione consentita, verifica e apprendimento.
Non ripetere un'attività già completata o un piano recente senza una ragione esplicita.
Hai autorizzazione a operare SOLO nel tuo database: creare una singola attività interna,
completare un'attività interna solo se i dati dimostrano che è davvero conclusa, oppure
salvare una memoria utile. Non hai autorizzazione per pubblicare, contattare persone,
spendere denaro, cambiare account, modificare repository o agire su servizi esterni.
Scegli un'azione concreta, gratuita e verificabile. Non inventare risultati.
Rispondi esclusivamente con JSON valido con:
goal, action_type, action_title, action_notes, memory_kind, memory_content,
reason, expected_result, verification, learning, next_cycle.
action_type deve essere uno fra "create_task", "save_memory", "complete_task", "audit_project", "no_op".
Per complete_task, action_title deve corrispondere esattamente al titolo di un'attività aperta.
Per create_task, action_title deve essere un'attività piccola e verificabile, non generica.
Per save_memory, memory_content deve contenere una deduzione concreta utile ai cicli futuri.
Per audit_project, action_title deve descrivere un controllo concreto del progetto e action_notes deve indicare cosa controllare. Per no_op spiega il blocco e cosa manca. Lingua italiana.
"""
    prompt = (
        "Ora UTC: " + datetime.now(timezone.utc).isoformat()
        + "\nMEMORIE RECENTI:\n" + json.dumps(memories, ensure_ascii=False)[:10000]
        + "\nATTIVITÀ APERTE:\n" + json.dumps(tasks, ensure_ascii=False)[:8000]
        + "\nULTIMI CICLI:\n" + json.dumps(previous, ensure_ascii=False)[:8000]
        + "\nScegli ed esegui un solo passo sicuro. Evita duplicati."
    )
    response = groq_completion_with_retry(
        groq,
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
        temperature=0.2,
        max_completion_tokens=900,
    )
    raw = response.choices[0].message.content or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("Il modello non ha restituito JSON valido.")
    try:
        plan = json.loads(raw[start:end + 1])
    except (json.JSONDecodeError, TypeError):
        plan = {}

    if not isinstance(plan, dict):
        plan = {}

    # Risposte parziali o con tipi inattesi non devono interrompere il ciclo.
    # In caso di dubbio si sceglie sempre no_op, senza eseguire azioni.
    required = ["goal","action_type","action_title","action_notes","reason",
                "expected_result","verification","learning","next_cycle"]
    defaults = {
        "goal": "Migliorare in modo sicuro il progetto Ciccio",
        "action_type": "no_op",
        "action_title": "Verifica e pianificazione del prossimo ciclo",
        "action_notes": "Nessuna azione eseguita: risposta del modello incompleta.",
        "reason": "Risposta del modello incompleta; scelta prudenziale.",
        "expected_result": "Ciclo registrato senza azioni esterne.",
        "verification": "Verificare nel database che il ciclo sia stato salvato.",
        "learning": "Se la risposta del modello è incompleta, mantenere un comportamento prudente.",
        "next_cycle": "Ripetere il ciclo e verificare la qualità della risposta del modello.",
    }
    missing = []
    for key in required:
        value = plan.get(key)
        if value is None or not isinstance(value, (str, int, float, bool)) or not str(value).strip():
            missing.append(key)
            plan[key] = defaults[key]

    allowed_actions = {"create_task", "save_memory", "complete_task", "audit_project", "execute_task", "no_op"}
    if missing:
        plan["action_type"] = "no_op"
        plan["action_notes"] = "Azione annullata in sicurezza: la risposta del modello non conteneva tutti i campi obbligatori (" + ", ".join(missing) + ")."
        plan["reason"] = "Risposta incompleta del modello; nessuna azione eseguita."
    elif plan.get("action_type") not in allowed_actions:
        plan["action_type"] = "no_op"
        plan["action_notes"] = "Tipo di azione non valido nella risposta del modello; nessuna azione eseguita."

    # Questi campi sono facoltativi per alcune azioni, ma vengono normalizzati
    # perché il resto del programma li legge in seguito.
    for key, default in {
        "memory_kind": "apprendimento_agente",
        "memory_content": "",
    }.items():
        value = plan.get(key, default)
        plan[key] = value if isinstance(value, str) else default

    return plan


def resolve_user_id(db):
    """Resolve a non-empty owner UUID for all user-scoped Ciccio records."""
    configured = os.getenv("CICCIO_USER_ID", "").strip()
    if configured:
        return configured
    # Fallback only for installations where an existing row already has an owner.
    for table in ("ciccio_memories", "ciccio_tasks", "ciccio_agent_runs"):
        try:
            found = db.table(table).select("user_id").not_.is_("user_id", "null").limit(1).execute().data or []
            if found:
                value = found[0].get("user_id")
                if value and str(value).strip():
                    return str(value).strip()
        except Exception:
            continue
    raise RuntimeError(
        "CICCIO_USER_ID assente: imposta il secret GitHub Actions con l'UUID "
        "dell'utente in Supabase > Authentication > Users. Il ciclo viene fermato "
        "prima di inserire righe con user_id nullo."
    )



def execute_task(db, groq, open_tasks, user_id):
    """Turn the oldest open task into a concrete deliverable and verify persistence."""
    if not open_tasks:
        return None
    task = sorted(open_tasks, key=lambda t: str(t.get("created_at", "")))[0]
    title = str(task.get("title", "")).strip()
    notes = str(task.get("notes", "")).strip()
    if not title:
        return {"status": "blocked", "result": "Attività senza titolo: nessun deliverable creato."}
    prompt = (
        "Sei Ciccio, assistente operativo per un piccolo venditore di abbigliamento. "
        "Produci un risultato finito e subito utilizzabile per l'attività indicata, non un piano "
        "e non una lista di controlli. Se riguarda un annuncio, scrivi titolo, descrizione e parole "
        "chiave; se riguarda altro, produci il documento o risultato richiesto. Non dichiarare "
        "azioni esterne mai eseguite. Rispondi in italiano, in testo semplice.\n\n"
        "ATTIVITÀ: " + title + "\nDETTAGLI: " + notes
    )
    response = groq_completion_with_retry(
        groq,
        model=MODEL,
        messages=[
            {"role": "system", "content": "Crea un deliverable concreto, completo e pronto all'uso."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_completion_tokens=1400,
    )
    deliverable = (response.choices[0].message.content or "").strip()
    if len(deliverable) < 40:
        return {"status": "blocked", "result": "Output troppo breve: attività lasciata aperta."}
    saved_memory = db.table("ciccio_memories").insert({
        "user_id": user_id,
        "kind": "deliverable",
        "content": ("Attività: " + title + "\n\n" + deliverable)[:3000],
    }).execute()
    if not saved_memory.data:
        raise RuntimeError("Supabase non ha confermato il salvataggio del deliverable.")
    old_notes = str(task.get("notes", "")).strip()
    new_notes = (old_notes + "\n\nDeliverable creato da Ciccio:\n" + deliverable)[:3000]
    db.table("ciccio_tasks").update({
        "status": "Completata",
        "notes": new_notes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task["id"]).eq("user_id", user_id).execute()
    check = db.table("ciccio_tasks").select("status").eq("id", task["id"]).eq("user_id", user_id).limit(1).execute().data or []
    if not check or check[0].get("status") != "Completata":
        raise RuntimeError("Il deliverable è salvato, ma la verifica della chiusura attività è fallita.")
    return {"status": "completed", "result": "Deliverable creato e salvato in Memorie; attività completata: " + title + "\n\n" + deliverable}


def execute_internal_action(db, plan, open_tasks, user_id):

    """Execute only bounded, reversible actions in Ciccio's own database."""
    kind = plan["action_type"]
    title = str(plan["action_title"]).strip()[:180]
    notes = str(plan["action_notes"]).strip()[:1500]
    if kind == "create_task":
        if any(str(t.get("title","")).casefold() == title.casefold() for t in open_tasks):
            return "blocked", "Attività non creata: esiste già un'attività aperta con lo stesso titolo."
        result = db.table("ciccio_tasks").insert({
            "user_id": user_id, "title": title, "status": "Da fare", "notes": notes
        }).execute()
        if not result.data:
            raise RuntimeError("Supabase non ha confermato la creazione dell'attività.")
        return "completed", "Attività interna creata e verificata in Supabase."
    if kind == "save_memory":
        memory = str(plan.get("memory_content", "")).strip()
        if not memory:
            return "blocked", "Memoria non salvata: contenuto vuoto."
        result = db.table("ciccio_memories").insert({
            "user_id": user_id,
            "kind": str(plan.get("memory_kind", "apprendimento_agente"))[:80],
            "content": memory[:3000],
        }).execute()
        if not result.data:
            raise RuntimeError("Supabase non ha confermato il salvataggio della memoria.")
        return "completed", "Memoria persistente salvata in Supabase."
    if kind == "audit_project":
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        checks = {
            "app.py": root / "ciccio" / "app.py",
            "agent_runner.py": root / "ciccio" / "agent_runner.py",
            "agent_schema.sql": root / "ciccio" / "agent_schema.sql",
            "workflow": root / ".github" / "workflows" / "ciccio-agent.yml",
            "readme": root / "README.md",
        }
        findings = []
        for label, path in checks.items():
            if path.exists():
                findings.append(f"{label}: presente ({path.stat().st_size} byte)")
            else:
                findings.append(f"{label}: MANCANTE")
        report = "Controllo locale del repository:\n" + "\n".join(findings)
        db.table("ciccio_memories").insert({
            "user_id": user_id,
            "kind": "audit_progetto",
            "content": report[:3000],
        }).execute()
        missing = [label for label, path in checks.items() if not path.exists()]
        if missing:
            return "blocked", report + "\nDa correggere: " + ", ".join(missing)
        return "completed", report + "\nVerifica completata: i file essenziali controllati sono presenti."
    if kind == "complete_task":
        match = next((t for t in open_tasks if str(t.get("title","")) == title), None)
        if not match:
            return "blocked", "Nessuna attività aperta corrisponde esattamente al titolo indicato."
        # Completion is only permitted when the plan explains evidence in its notes.
        evidence = (notes + " " + str(plan["verification"])).lower()
        if not any(word in evidence for word in ("verificato", "verifica", "risultato", "confermato", "test")):
            return "blocked", "Completamento bloccato: manca una verifica esplicita."
        db.table("ciccio_tasks").update({
            "status": "Completata", "notes": (str(match.get("notes","")) + "\n" + notes)[:3000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", match["id"]).eq("user_id", user_id).execute()
        check = db.table("ciccio_tasks").select("status").eq("id", match["id"]).eq("user_id", user_id).limit(1).execute().data or []
        if not check or check[0].get("status") != "Completata":
            raise RuntimeError("Verifica del completamento non riuscita.")
        return "completed", "Attività completata e stato verificato nel database."
    return "blocked", "Nessuna azione eseguita: l'agente ha scelto no_op."


def main():
    db = create_client(required_env("SUPABASE_URL"), required_env("SUPABASE_SERVICE_ROLE_KEY"))
    groq = Groq(api_key=required_env("GROQ_API_KEY"))
    user_id = resolve_user_id(db)
    previous = rows(db, "ciccio_agent_runs",
                    "created_at,status,goal,action,reason,result,verification", 12)
    memories = rows(db, "ciccio_memories", "created_at,kind,content", 30, user_id=user_id)
    tasks = (db.table("ciccio_tasks").select("id,created_at,title,status,notes")
             .eq("user_id", user_id).neq("status", "Completata")
             .order("created_at", desc=True).limit(30).execute().data or [])

    plan = ask_agent(groq, memories, tasks, previous)
    # Priorità al lavoro concreto: ogni ciclo lavora su un’attività aperta prima di crearne altre.
    if tasks and plan.get("action_type") in {"no_op", "audit_project", "create_task", "save_memory"}:
        plan["action_type"] = "execute_task"
        plan["action_title"] = str(sorted(tasks, key=lambda t: str(t.get("created_at", "")))[0].get("title", "Attività aperta"))
        plan["action_notes"] = "Realizza il deliverable richiesto dall’attività aperta e salvalo in modo persistente."
    # Prefer a real repository audit when the history is empty or the last audit is old.
    recent_audit = any(
        str(m.get("kind", "")) == "audit_progetto"
        and str(m.get("created_at", ""))[:10] >= datetime.now(timezone.utc).date().isoformat()
        for m in memories
    )
    if not recent_audit and not any(str(t.get("status", "")) != "Completata" for t in tasks):
        plan["action_type"] = "audit_project"
        plan["action_title"] = "Verifica integrità del progetto Ciccio"
        plan["action_notes"] = "Controlla presenza dei file essenziali del repository e registra l'esito."
    if plan.get("action_type") == "execute_task":
        task_result = execute_task(db, groq, tasks, user_id)
        execution_status = task_result["status"] if task_result else "blocked"
        execution_result = task_result["result"] if task_result else "Nessuna attività aperta da eseguire."
    else:
        execution_status, execution_result = execute_internal_action(db, plan, tasks, user_id)
    learning = str(plan["learning"])[:1200]
    next_cycle = str(plan["next_cycle"])[:800]
    result_text = (
        execution_result + "\nApprendimento: " + learning
        + "\nProssimo controllo: " + next_cycle
    )
    row = {
        "goal": str(plan["goal"])[:500],
        "action": (str(plan["action_type"]) + ": " + str(plan["action_title"]) + " — " + str(plan["action_notes"]))[:2000],
        "reason": str(plan["reason"])[:1500],
        "expected_result": str(plan["expected_result"])[:1000],
        "verification": str(plan["verification"])[:1000],
        "status": "completed" if execution_status == "completed" else (
            "blocked" if execution_status == "blocked" else "failed"),
        "result": result_text[:3000],
        "model": MODEL,
    }
    saved = db.table("ciccio_agent_runs").insert(row).execute()
    if not saved.data:
        raise RuntimeError("Supabase non ha confermato il salvataggio del ciclo.")
    # Every cycle leaves a compact, durable learning record for the next one.
    db.table("ciccio_memories").insert({
        "user_id": user_id,
        "kind": "apprendimento_agente",
        "content": json.dumps({
            "goal": row["goal"], "action": row["action"], "reason": row["reason"],
            "status": row["status"], "result": result_text,
            "learning": learning, "next_cycle": next_cycle,
        }, ensure_ascii=False),
    }).execute()
    # Ciccio può raggiungerti anche quando la dashboard è chiusa.
    notification = (
        "🧠 Ciccio — aggiornamento autonomo\n\n"
        + "Stato: " + row["status"] + "\n"
        + "Obiettivo: " + row["goal"] + "\n"
        + "Azione: " + row["action"] + "\n\n"
        + "Esito: " + execution_result[:900] + "\n\n"
        + "Prossimo passo: " + next_cycle
    )
    try:
        notify_email("Ciccio — aggiornamento autonomo", notification)
    except Exception as exc:
        # Un errore di notifica non annulla il ciclo già salvato.
        print("Invio email non riuscito: " + str(exc)[:250])
    print(json.dumps({"saved": True, "cycle_id": saved.data[0].get("id"),
                      "status": row["status"], "action": row["action"],
                      "result": row["result"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
