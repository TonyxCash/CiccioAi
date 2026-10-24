"""Ciccio autonomous agent cycle.
Autonomy is currently bounded to safe actions inside its own Supabase workspace:
create/update tasks and save durable memories. External actions require approval.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from groq import Groq
from supabase import create_client

MODEL = "openai/gpt-oss-20b"


def notify_user(message):
    """Send an autonomous Telegram message when optional secrets are configured."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram non configurato: ciclo salvato senza invio esterno.")
        return False
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message[:3900],
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram non ha confermato l'invio del messaggio.")
    print("Notifica Telegram inviata e confermata.")
    return True


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def rows(db, table, columns, limit, order="created_at"):
    return db.table(table).select(columns).order(order, desc=True).limit(limit).execute().data or []


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
    response = groq.chat.completions.create(
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
        temperature=0.2,
        max_completion_tokens=900,
    )
    raw = response.choices[0].message.content or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("Il modello non ha restituito JSON valido.")
    plan = json.loads(raw[start:end + 1])
    required = ["goal","action_type","action_title","action_notes","reason",
                "expected_result","verification","learning","next_cycle"]
    if any(not str(plan.get(k, "")).strip() for k in required):
        raise RuntimeError("Risposta incompleta: manca un campo obbligatorio.")
    if plan["action_type"] not in {"create_task","save_memory","complete_task","no_op"}:
        raise RuntimeError("Tipo di azione non consentito.")
    return plan


def execute_internal_action(db, plan, open_tasks):
    """Execute only bounded, reversible actions in Ciccio's own database."""
    kind = plan["action_type"]
    title = str(plan["action_title"]).strip()[:180]
    notes = str(plan["action_notes"]).strip()[:1500]
    if kind == "create_task":
        if any(str(t.get("title","")).casefold() == title.casefold() for t in open_tasks):
            return "blocked", "Attività non creata: esiste già un'attività aperta con lo stesso titolo."
        result = db.table("ciccio_tasks").insert({
            "title": title, "status": "Da fare", "notes": notes
        }).execute()
        if not result.data:
            raise RuntimeError("Supabase non ha confermato la creazione dell'attività.")
        return "completed", "Attività interna creata e verificata in Supabase."
    if kind == "save_memory":
        memory = str(plan.get("memory_content", "")).strip()
        if not memory:
            return "blocked", "Memoria non salvata: contenuto vuoto."
        result = db.table("ciccio_memories").insert({
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
        }).eq("id", match["id"]).execute()
        check = db.table("ciccio_tasks").select("status").eq("id", match["id"]).limit(1).execute().data or []
        if not check or check[0].get("status") != "Completata":
            raise RuntimeError("Verifica del completamento non riuscita.")
        return "completed", "Attività completata e stato verificato nel database."
    return "blocked", "Nessuna azione eseguita: l'agente ha scelto no_op."


def main():
    db = create_client(required_env("SUPABASE_URL"), required_env("SUPABASE_SERVICE_ROLE_KEY"))
    groq = Groq(api_key=required_env("GROQ_API_KEY"))
    previous = rows(db, "ciccio_agent_runs",
                    "created_at,status,goal,action,reason,result,verification", 12)
    memories = rows(db, "ciccio_memories", "created_at,kind,content", 30)
    tasks = (db.table("ciccio_tasks").select("id,created_at,title,status,notes")
             .neq("status", "Completata").order("created_at", desc=True)
             .limit(30).execute().data or [])

    plan = ask_agent(groq, memories, tasks, previous)
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
    execution_status, execution_result = execute_internal_action(db, plan, tasks)
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
        notify_user(notification)
    except Exception as exc:
        # Un errore di notifica non annulla il ciclo già salvato.
        print("Invio Telegram non riuscito: " + str(exc)[:250])
    print(json.dumps({"saved": True, "cycle_id": saved.data[0].get("id"),
                      "status": row["status"], "action": row["action"],
                      "result": row["result"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
