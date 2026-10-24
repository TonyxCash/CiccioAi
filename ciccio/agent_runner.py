"""Ciccio autonomous cycle: plan one useful task and persist the result.
This first version plans and logs; it does not spend money or perform external actions.
"""
import json
import os
from datetime import datetime, timezone

from groq import Groq
from supabase import create_client


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    groq_key = required_env("GROQ_API_KEY")
    supabase_url = required_env("SUPABASE_URL")
    supabase_key = required_env("SUPABASE_SERVICE_ROLE_KEY")

    db = create_client(supabase_url, supabase_key)
    previous = (
        db.table("ciccio_agent_runs")
        .select("created_at,status,goal,action,result")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
        .data
        or []
    )

    system_prompt = """
Sei Ciccio, un agente autonomo che cerca di mantenersi operativo e creare valore
partendo da zero euro. Ogni ciclo deve proporre UNA sola azione concreta, legale,
realistica, reversibile e gratuita, orientata a creare entrate future o migliorare
il sistema. Non promettere guadagni e non inventare risultati. Non spendere denaro,
non aprire account, non contattare persone, non pubblicare contenuti e non compiere
azioni esterne senza approvazione umana. Evita di ripetere le azioni recenti.
Rispondi SOLO con JSON valido con le chiavi: goal, action, reason, expected_result,
verification, status. status deve essere "planned". Scrivi in italiano.
L'azione deve essere piccola e verificabile in un singolo ciclo.
"""
    user_prompt = (
        "Data e ora UTC: " + datetime.now(timezone.utc).isoformat()
        + "\nUltimi cicli registrati: " + json.dumps(previous, ensure_ascii=False)
        + "\nScegli la prossima azione utile. Considera che il sistema è ancora in fase iniziale."
    )

    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_completion_tokens=600,
    )
    raw = response.choices[0].message.content or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("The model did not return valid JSON.")
    plan = json.loads(raw[start : end + 1])

    required_fields = ["goal", "action", "reason", "expected_result", "verification"]
    if any(not str(plan.get(field, "")).strip() for field in required_fields):
        raise RuntimeError("The plan is missing required fields.")

    row = {
        "goal": str(plan["goal"])[:500],
        "action": str(plan["action"])[:2000],
        "reason": str(plan["reason"])[:1500],
        "expected_result": str(plan["expected_result"])[:1000],
        "verification": str(plan["verification"])[:1000],
        "status": "planned",
        "result": "Piano generato automaticamente; nessuna azione esterna eseguita.",
        "model": "openai/gpt-oss-20b",
    }
    saved = db.table("ciccio_agent_runs").insert(row).execute()
    if not saved.data:
        raise RuntimeError("Supabase did not confirm saving the agent run.")
    print(json.dumps({"saved": True, "plan": row}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
