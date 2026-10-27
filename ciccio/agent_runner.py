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


def is_transient_error(exc):
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    return (
        status in {408, 425, 429}
        or (isinstance(status, int) and status >= 500)
        or any(token in name for token in ("timeout", "connection", "temporarilyunavailable"))
    )


def execute_read_with_retry(query, *, attempts=3):
    """Retry safe, read-only Supabase queries on transient transport/service errors."""
    for attempt in range(attempts):
        try:
            return query.execute()
        except Exception as exc:
            if not is_transient_error(exc) or attempt >= attempts - 1:
                raise
            delay = min(2 ** attempt, 4)
            print(f"Errore temporaneo nella lettura Supabase ({type(exc).__name__}); nuovo tentativo tra {delay}s.")
            time.sleep(delay)


def groq_completion_with_retry(groq, *, attempts=3, **kwargs):
    """Retry only transient Groq/API transport failures; never repeat database actions."""
    for attempt in range(attempts):
        try:
            return groq.chat.completions.create(**kwargs)
        except Exception as exc:
            if not is_transient_error(exc) or attempt >= attempts - 1:
                raise
            delay = min(2 ** attempt, 4)
            print(f"Errore temporaneo Groq ({type(exc).__name__}); nuovo tentativo tra {delay}s ({attempt + 2}/{attempts}).")
            time.sleep(delay)


def notify_email(subject, message):
    """Send Ciccio's cycle summary by email when SMTP secrets are configured."""
    import re
    import unicodedata
    from email.policy import SMTP

    def clean(value, *, preserve_lines=False):
        value = unicodedata.normalize("NFKC", str(value or ""))
        value = value.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2007", " ")
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        if preserve_lines:
            lines = [re.sub(r"[\t ]+", " ", line).strip() for line in value.split("\n")]
            # Keep intentional paragraphs, but remove excessive blank lines.
            normalized = []
            blank_pending = False
            for line in lines:
                if not line:
                    if normalized and not blank_pending:
                        normalized.append("")
                    blank_pending = True
                else:
                    normalized.append(line)
                    blank_pending = False
            return "\n".join(normalized).strip()
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
        # Preserve paragraphs and Italian accents; quoted-printable safely encodes UTF-8.
        body = clean(message, preserve_lines=True)
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
def notify_telegram(message):
    """Send a status alert only when the owner explicitly configured bot credentials."""
    import urllib.request

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    payload = json.dumps({
        "chat_id": chat_id,
        "text": str(message or "")[:3500],
        "disable_web_page_preview": True,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            print("Notifica Telegram non confermata dall'API.")
            return False
        print("Notifica Telegram inviata.")
        return True
    except Exception as exc:
        # The Telegram bot token is part of the request URL; never print it in workflow logs.
        safe_detail = str(exc).replace(token, "[REDACTED]")[:180]
        print("Notifica Telegram non riuscita: " + type(exc).__name__ + ": " + safe_detail)
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
    return execute_read_with_retry(query.order(order, desc=True).limit(limit)).data or []


def failed_task_attempts(task, previous):
    """Count recent blocked/failed executions for this task since its last manual update."""
    title = str(task.get("title", "")).strip()
    if not title:
        return 0
    prefix = "execute_task: " + title
    updated_at = None
    try:
        updated_raw = str(task.get("updated_at", "")).replace("Z", "+00:00")
        if updated_raw:
            updated_at = datetime.fromisoformat(updated_raw)
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        updated_at = None

    count = 0
    for run in previous:
        if run.get("status") not in {"blocked", "failed"}:
            continue
        if not str(run.get("action", "")).startswith(prefix):
            continue
        if updated_at is not None:
            try:
                run_raw = str(run.get("created_at", "")).replace("Z", "+00:00")
                run_at = datetime.fromisoformat(run_raw)
                if run_at.tzinfo is None:
                    run_at = run_at.replace(tzinfo=timezone.utc)
                if run_at <= updated_at:
                    continue
            except (TypeError, ValueError):
                pass
        count += 1
    return count


def ask_agent(groq, memories, tasks, previous):
    system = """
Sei Ciccio, agente persistente con obiettivo stabile: lavorare in cicli di memoria,
ragionamento, decisione, azione consentita, verifica e apprendimento.
Missione: aiutare l'utente a ottenere entrate reali con budget zero o minimo, dando priorità
a rendere ListingAI utilizzabile e validarlo con venditori reali; in parallelo può preparare materiali
pronti all'uso per la vendita di abbigliamento Jhavè. Ogni ciclo deve produrre progresso concreto,
non solo rapporti, audit di presenza file o nuove liste generiche.
Quando non ci sono attività aperte, crea una sola attività piccola che possa produrre un deliverable
utilizzabile nel ciclo successivo. Dai priorità a: miglioramenti MVP di ListingAI, test pratici,
messaggi/materiali per trovare i primi utenti, e contenuti di vendita pronti da pubblicare.
Preferisci risultati che aiutino a ottenere feedback o ricavi senza pubblicità a pagamento.
Usa le memorie, le attività e il codice del repository disponibile come fonte primaria; non inventare
dati di mercato, risultati, utenti contattati o preferenze. Non ripetere attività completate senza motivo.
Hai autorizzazione a operare SOLO nel tuo database: creare una singola attività interna
oppure salvare una memoria utile. Non dichiarare completata un'attività sulla sola base del piano:
il runner la completa soltanto dopo aver prodotto e verificato un deliverable salvato.
Non hai autorizzazione per pubblicare, contattare persone, spendere denaro, cambiare account,
modificare repository o agire su servizi esterni.
Scegli un'azione concreta, gratuita e verificabile. Non inventare risultati.
Rispondi esclusivamente con JSON valido con:
goal, action_type, action_title, action_notes, memory_kind, memory_content,
reason, expected_result, verification, learning, next_cycle.
action_type deve essere uno fra "create_task", "save_memory", "audit_project", "no_op". Non segnare attività come completate solo sulla base di una tua affermazione: l'agente le completa esclusivamente dopo aver prodotto e salvato un deliverable verificabile.
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

    allowed_actions = {"create_task", "save_memory", "audit_project", "no_op"}
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
    for table in ("ciccio_memories", "ciccio_tasks"):
        try:
            found = execute_read_with_retry(db.table(table).select("user_id").not_.is_("user_id", "null").limit(1)).data or []
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
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    project_context = []
    for label, path in (
        ("app.py", root / "app.py"),
        ("README.md", root / "README.md"),
        ("requirements.txt", root / "requirements.txt"),
    ):
        try:
            if path.is_file():
                project_context.append("### " + label + "\\n" + path.read_text(encoding="utf-8")[:4500])
        except (OSError, UnicodeError):
            project_context.append("### " + label + "\\nFile presente ma non leggibile.")
    context_text = "\\n\\n".join(project_context)[:11000]
    prompt = (
        "Sei Ciccio, agente operativo orientato a risultati e ricavi a budget zero. "
        "Produci un deliverable finito, concreto e immediatamente utilizzabile, non una promessa "
        "di lavoro futuro. Se l'attività riguarda ListingAI, usa il codice e la documentazione "
        "qui sotto per essere specifico; non affermare di aver modificato il repository perché "
        "non hai permessi per farlo. Se riguarda annunci, scrivi testo pronto da usare. "
        "Se riguarda validazione commerciale, prepara materiali e una procedura pratica, ma non "
        "dichiarare di aver contattato utenti o ottenuto risposte. Italiano, testo semplice.\\n\\n"
        "ATTIVITÀ: " + title + "\\nDETTAGLI: " + notes
        + "\\n\\nCONTESTO REALE DEL REPOSITORY:\\n" + context_text
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
    old_notes = str(task.get("notes", "")).strip()
    deliverable_block = "Deliverable creato da Ciccio:\n" + deliverable
    # Keep a short excerpt of the original request while reserving space for the result.
    new_notes = ((old_notes[:500] + "\n\n") if old_notes else "") + deliverable_block
    new_notes = new_notes[:3000]
    db.table("ciccio_tasks").update({
        "status": "Completata",
        "notes": new_notes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task["id"]).eq("user_id", user_id).execute()
    check = execute_read_with_retry(db.table("ciccio_tasks").select("status,notes").eq("id", task["id"]).eq("user_id", user_id).limit(1)).data or []
    if (
        not check
        or check[0].get("status") != "Completata"
        or "Deliverable creato da Ciccio:" not in str(check[0].get("notes", ""))
        or deliverable[:100] not in str(check[0].get("notes", ""))
    ):
        raise RuntimeError("Il deliverable è stato generato, ma il salvataggio o la chiusura non è stato verificato.")
    # Store the separate memory only after the task is safely marked complete.
    # If this insert fails, the deliverable remains in task notes and won't be regenerated next cycle.
    saved_memory = db.table("ciccio_memories").insert({
        "user_id": user_id,
        "kind": "deliverable",
        "content": ("Attività: " + title + "\n\n" + deliverable)[:3000],
    }).execute()
    if not saved_memory.data:
        raise RuntimeError("Attività completata e deliverable presente nelle note, ma memoria separata non confermata.")
    return {"status": "completed", "result": "Deliverable creato, salvato nelle note dell'attività e in Memorie; attività completata: " + title + "\n\n" + deliverable}


def execute_internal_action(db, plan, open_tasks, user_id):

    """Execute only bounded, reversible actions in Ciccio's own database."""
    kind = plan["action_type"]
    title = str(plan["action_title"]).strip()[:180]
    notes = str(plan["action_notes"]).strip()[:1500]
    if kind == "create_task":
        existing_tasks = execute_read_with_retry(
            db.table("ciccio_tasks").select("title,status")
            .eq("user_id", user_id).order("created_at", desc=True).limit(100)
        ).data or []
        if any(str(t.get("title", "")).strip().casefold() == title.casefold() for t in existing_tasks):
            return "blocked", "Attività non creata: esiste già un'attività con lo stesso titolo, anche se completata."
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
        memory_kind = str(plan.get("memory_kind", "apprendimento_agente"))[:80]
        existing_memories = execute_read_with_retry(
            db.table("ciccio_memories").select("id")
            .eq("user_id", user_id).eq("kind", memory_kind)
            .eq("content", memory[:3000]).limit(1)
        ).data or []
        if existing_memories:
            return "blocked", "Memoria non duplicata: esiste già un record identico."
        result = db.table("ciccio_memories").insert({
            "user_id": user_id,
            "kind": memory_kind,
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
        audit_saved = db.table("ciccio_memories").insert({
            "user_id": user_id,
            "kind": "audit_progetto",
            "content": report[:3000],
        }).execute()
        if not audit_saved.data:
            raise RuntimeError("Supabase non ha confermato il salvataggio del rapporto di audit.")
        missing = [label for label, path in checks.items() if not path.exists()]
        if missing:
            return "blocked", report + "\nDa correggere: " + ", ".join(missing)
        return "completed", report + "\nVerifica completata: i file essenziali controllati sono presenti."
    return "blocked", "Nessuna azione eseguita: l'agente ha scelto no_op."


def record_failure(db, stage, exc, plan=None):
    """Persist a compact failure record without hiding the original exception."""
    plan = plan if isinstance(plan, dict) else {}
    detail = (type(exc).__name__ + ": " + str(exc))[:1800]
    row = {
        "goal": str(plan.get("goal") or "Esecuzione ciclo Ciccio")[:500],
        "action": (str(plan.get("action_type") or "cycle") + ": "
                   + str(plan.get("action_title") or "Errore durante il ciclo"))[:2000],
        "reason": ("Errore nella fase: " + str(stage))[:1500],
        "expected_result": str(plan.get("expected_result") or "Ciclo completato e salvato")[:1000],
        "verification": "Controllare il log e riprendere dal prossimo ciclo; non ripetere automaticamente azioni database.",
        "status": "failed",
        "result": (detail + "\nFase: " + str(stage))[:3000],
        "model": MODEL,
    }
    try:
        result = db.table("ciccio_agent_runs").insert(row).execute()
        if not result.data:
            print("Registro errore non confermato da Supabase.")
            return False
        print("Errore registrato in ciccio_agent_runs.")
        return True
    except Exception as log_exc:
        print("Impossibile registrare l'errore in Supabase: "
              + (type(log_exc).__name__ + ": " + str(log_exc))[:300])
        return False


def main():
    db = None
    plan = {}
    stage = "inizializzazione Supabase"
    try:
        db = create_client(required_env("SUPABASE_URL"), required_env("SUPABASE_SERVICE_ROLE_KEY"))
        stage = "inizializzazione modello AI"
        groq = Groq(api_key=required_env("GROQ_API_KEY"))
        stage = "identificazione utente"
        user_id = resolve_user_id(db)
        stage = "lettura storico"
        previous = rows(db, "ciccio_agent_runs",
                        "created_at,status,goal,action,reason,result,verification", 12)
        memories = rows(db, "ciccio_memories", "created_at,kind,content", 30, user_id=user_id)
        tasks = execute_read_with_retry(
            db.table("ciccio_tasks").select("id,created_at,updated_at,title,status,notes")
            .eq("user_id", user_id).neq("status", "Completata").neq("status", "Bloccata")
            .order("created_at", desc=True).limit(30)
        ).data or []

        # Pause a task after three recent failures; a later manual edit resets its retry window.
        active_tasks = []
        for task in tasks:
            if failed_task_attempts(task, previous) >= 3:
                pause_note = "Ciccio: attività sospesa automaticamente dopo 3 tentativi falliti. Correggi le note e reimposta lo stato per riprovare."
                updated_notes = (str(task.get("notes", "")).strip()[:1500] + "\n\n" + pause_note).strip()[:3000]
                db.table("ciccio_tasks").update({
                    "status": "Bloccata",
                    "notes": updated_notes,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", task["id"]).eq("user_id", user_id).neq("status", "Completata").execute()
                check = execute_read_with_retry(
                    db.table("ciccio_tasks").select("status,notes")
                    .eq("id", task["id"]).eq("user_id", user_id).limit(1)
                ).data or []
                if not check or check[0].get("status") != "Bloccata" or pause_note not in str(check[0].get("notes", "")):
                    raise RuntimeError("La sospensione dell'attività dopo tentativi falliti non è stata verificata.")
                print("Attività sospesa dopo tre tentativi falliti: " + str(task.get("title", ""))[:150])
            else:
                active_tasks.append(task)
        tasks = active_tasks

        stage = "pianificazione AI"
        plan = ask_agent(groq, memories, tasks, previous)
        # Priorità al lavoro concreto: ogni ciclo lavora su un’attività aperta prima di crearne altre.
        if tasks and plan.get("action_type") in {"no_op", "audit_project", "create_task", "save_memory"}:
            plan["action_type"] = "execute_task"
            plan["action_title"] = str(sorted(tasks, key=lambda t: str(t.get("created_at", "")))[0].get("title", "Attività aperta"))
            plan["action_notes"] = "Realizza il deliverable richiesto dall’attività aperta e salvalo in modo persistente."
        # Never spend an empty-work cycle on a routine file-presence audit.
        # If no task is open, require the planner to create a concrete next deliverable.
        if not tasks and plan.get("action_type") != "create_task":
            plan["action_type"] = "create_task"
            plan["goal"] = "Produrre progressi concreti verso le prime entrate senza pubblicità a pagamento"
            plan["action_title"] = "ListingAI — preparare il prossimo deliverable per validare l'MVP"
            plan["action_notes"] = (
                "Esamina il contesto del repository e crea un deliverable concreto e pronto all'uso "
                "per migliorare ListingAI o validarlo con i primi venditori. Deve essere piccolo, "
                "misurabile, a costo zero e diverso dai deliverable già presenti nelle memorie. "
                "Non creare una semplice lista generica di idee."
            )
            plan["reason"] = "Non ci sono attività aperte: serve un prossimo passo concreto verso un prodotto utilizzabile e ricavi."
            plan["expected_result"] = "Una singola attività verificabile con un risultato utilizzabile nel ciclo successivo."
            plan["verification"] = "Il ciclo successivo deve salvare il deliverable nelle note e nelle memorie di Supabase."

        stage = "esecuzione azione"
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
        stage = "salvataggio log del ciclo"
        saved = db.table("ciccio_agent_runs").insert(row).execute()
        if not saved.data:
            raise RuntimeError("Supabase non ha confermato il salvataggio del ciclo.")

        stage = "salvataggio apprendimento"
        learning_saved = db.table("ciccio_memories").insert({
            "user_id": user_id,
            "kind": "apprendimento_agente",
            "content": json.dumps({
                "goal": row["goal"], "action": row["action"], "reason": row["reason"],
                "status": row["status"], "result": result_text,
                "learning": learning, "next_cycle": next_cycle,
            }, ensure_ascii=False),
        }).execute()
        if not learning_saved.data:
            raise RuntimeError("Supabase non ha confermato il salvataggio dell'apprendimento.")

        stage = "notifica email"
        status_labels = {
            "completed": "Completato",
            "blocked": "In pausa",
            "failed": "Richiede attenzione",
        }
        action_title = str(plan.get("action_title") or "Attività del ciclo").strip()
        notification = (
            "CICCIO | RESOCONTO DEL CICLO\n"
            "--------------------------------\n\n"
            + "Stato: " + status_labels.get(row["status"], "Registrato") + "\n"
            + "Obiettivo\n" + str(row["goal"]).strip() + "\n\n"
            + "Attività svolta\n" + action_title + "\n\n"
            + "Risultato\n" + str(execution_result).strip()[:1200] + "\n\n"
            + "Prossimo passo\n" + str(next_cycle).strip() + "\n\n"
            + "Il resoconto completo è disponibile nella dashboard di Ciccio."
        )
        try:
            notify_email("Ciccio | Resoconto del ciclo", notification)
        except Exception as exc:
            # Un errore di notifica non annulla il ciclo già salvato.
            print("Invio email non riuscito: " + str(exc)[:250])
        notify_telegram(notification)
        print(json.dumps({"saved": True, "cycle_id": saved.data[0].get("id"),
                          "status": row["status"], "action": row["action"],
                          "result": row["result"]}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print("Ciclo Ciccio fallito nella fase '" + stage + "': "
              + (type(exc).__name__ + ": " + str(exc))[:1200])
        if db is not None:
            record_failure(db, stage, exc, plan)
        try:
            notify_email(
                "Ciccio | Ciclo da controllare",
                "CICCIO | AVVISO DI ESECUZIONE\n"
                "--------------------------------\n\n"
                "Il ciclo automatico non si è concluso correttamente.\n\n"
                "Fase interessata\n" + str(stage) + "\n\n"
                "Dettaglio tecnico\n" + (type(exc).__name__ + ": " + str(exc))[:900] + "\n\n"
                "L'errore è stato registrato in Supabase, se il database era disponibile. "
                "Ciccio non ripete automaticamente questo ciclo per evitare duplicazioni."
            )
        except Exception as notify_exc:
            print("Notifica email errore non riuscita: " + str(notify_exc)[:200])
        notify_telegram(
            "Ciccio — errore nel ciclo autonomo\nFase: " + stage
            + "\nErrore: " + (type(exc).__name__ + ": " + str(exc))[:700]
        )
        raise


if __name__ == "__main__":
    main()
