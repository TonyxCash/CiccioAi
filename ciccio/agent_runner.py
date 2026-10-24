"""Ciccio: persistent autonomous planning/learning cycle.
This cycle reads long-term memory and open tasks, creates one verifiable next step,
and records the decision and its rationale. External actions remain approval-gated.
"""
import json
import os
from datetime import datetime, timezone

from groq import Groq
from supabase import create_client


MODEL = "openai/gpt-oss-20b"


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_rows(db, table: str, columns: str, limit: int, order: str = "created_at"):
    return (
        db.table(table).select(columns).order(order, desc=True).limit(limit).execute().data
        or []
    )


def main() -> None:
    db = create_client(
        required_env("SUPABASE_URL"),
        required_env("SUPABASE_SERVICE_ROLE_KEY"),
    )
    groq = Groq(api_key=required_env("GROQ_API_KEY"))

    previous = read_rows(
        db, "ciccio_agent_runs",
        "created_at,status,goal,action,result,verification", 10
    )
    memories = read_rows(db, "ciccio_memories", "created_at,kind,content", 30)
    tasks = (
        db.table("ciccio_tasks")
        .select("created_at,title,status,notes")
        .neq("status", "Completata")
        .order("created_at", desc=True)
        .limit(20)
        .execute().data or []
    )

    system_prompt = """
Sei Ciccio, un agente AI persistente con una missione stabile: diventare più utile
attraverso cicli ripetuti di memoria, ragionamento, scelta, azione consentita,
verifica e apprendimento. Non sei un semplice generatore di idee: devi usare le
memorie, i risultati precedenti e le attività aperte per decidere il prossimo passo.
Preferisci continuità e progresso misurabile, evita di ripetere piani recenti senza
spiegare perché. In questa fase puoi leggere e scrivere nel database del progetto,
ma non hai accesso autorizzato ad altri sistemi o strumenti di esecuzione.
Non dichiarare completata un'azione che non hai eseguito e verificato. Non spendere,
non contattare persone, non pubblicare, non aprire account, non modificare dati esterni
e non eseguire azioni irreversibili senza approvazione umana.
Scegli un passo gratuito, legale, concreto e verificabile che faccia avanzare la
missione oppure migliori l'affidabilità dell'agente. Se non puoi procedere, indica
con precisione il blocco. Scrivi in italiano.
Rispondi SOLO con JSON valido con queste chiavi:
goal, action, reason, expected_result, verification, learning, next_cycle,
status.
status deve essere "planned". learning deve dire cosa hai dedotto dalle memorie e
dai cicli precedenti; next_cycle deve indicare cosa controllare nel ciclo seguente.
"""
    user_prompt = (
        "Ora UTC: " + datetime.now(timezone.utc).isoformat()
        + "\nMEMORIA PERSISTENTE RECENTE:\n"
        + json.dumps(memories, ensure_ascii=False)[:12000]
        + "\nATTIVITÀ APERTE:\n"
        + json.dumps(tasks, ensure_ascii=False)[:8000]
        + "\nULTIMI CICLI E RISULTATI:\n"
        + json.dumps(previous, ensure_ascii=False)[:10000]
        + "\nGenera il prossimo passo usando davvero questi dati."
    )

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_completion_tokens=900,
    )
    raw = response.choices[0].message.content or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("Il modello non ha restituito JSON valido.")
    plan = json.loads(raw[start:end + 1])

    required_fields = [
        "goal", "action", "reason", "expected_result",
        "verification", "learning", "next_cycle"
    ]
    if any(not str(plan.get(field, "")).strip() for field in required_fields):
        raise RuntimeError("Il piano è incompleto: manca uno o più campi obbligatori.")
    if plan.get("status") != "planned":
        raise RuntimeError("Stato non valido: il ciclo deve restare planned.")

    row = {
        "goal": str(plan["goal"])[:500],
        "action": str(plan["action"])[:2000],
        "reason": str(plan["reason"])[:1500],
        "expected_result": str(plan["expected_result"])[:1000],
        "verification": str(plan["verification"])[:1000],
        "status": "planned",
        "result": "Piano registrato. Nessuna azione esterna è stata eseguita. "
                  "Apprendimento: " + str(plan["learning"])[:1200]
                  + " Prossimo controllo: " + str(plan["next_cycle"])[:800],
        "model": MODEL,
    }
    saved = db.table("ciccio_agent_runs").insert(row).execute()
    if not saved.data:
        raise RuntimeError("Supabase non ha confermato il salvataggio del ciclo.")

    # Keep a compact learning trail so future cycles can use it as long-term context.
    db.table("ciccio_memories").insert({
        "kind": "apprendimento_agente",
        "content": json.dumps({
            "goal": row["goal"],
            "decision": row["action"],
            "reason": row["reason"],
            "learning": str(plan["learning"])[:1200],
            "next_cycle": str(plan["next_cycle"])[:800],
            "status": row["status"],
        }, ensure_ascii=False),
    }).execute()

    print(json.dumps({
        "saved": True,
        "cycle_id": saved.data[0].get("id"),
        "plan": row,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
