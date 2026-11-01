import { NextRequest, NextResponse } from "next/server";
import { isAuthenticated } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Config = { base: string; key: string; user: string; groq: string; openrouter: string };
type MemoryRow = { created_at: string; kind: string; content: string };
type TaskRow = { id: string; title: string; status: string; notes: string; created_at?: string; updated_at?: string };

function config(): Config {
  const base = (process.env.SUPABASE_URL || "").replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || "";
  const user = process.env.CICCIO_USER_ID || "";
  const groq = process.env.GROQ_API_KEY || "";
  const openrouter = process.env.OPENROUTER_API_KEY || "";
  if (!base || !key || !user || !groq) throw new Error("Configurazione server incompleta: controlla le variabili di Ciccio su Vercel.");
  return { base, key, user, groq, openrouter };
}

function headers(c: Config) {
  return { apikey: c.key, Authorization: "Bearer " + c.key };
}

async function readMemory(c: Config): Promise<MemoryRow[]> {
  const url = c.base + "/rest/v1/ciccio_memories?select=created_at,kind,content&user_id=eq." + encodeURIComponent(c.user) + "&order=created_at.desc&limit=30";
  const r = await fetch(url, { headers: headers(c), cache: "no-store" });
  if (!r.ok) throw new Error("Lettura memoria non riuscita (" + r.status + ").");
  return await r.json() as MemoryRow[];
}

async function saveRows(c: Config, items: Array<{ kind: string; content: string }>) {
  const r = await fetch(c.base + "/rest/v1/ciccio_memories", {
    method: "POST",
    headers: { ...headers(c), "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify(items.map(x => ({ ...x, user_id: c.user })))
  });
  if (!r.ok) throw new Error("Salvataggio conversazione non riuscito (" + r.status + ").");
}

function cleanText(value: unknown, max = 3000): string {
  return String(value ?? "").replace(/\u0000/g, "").trim().slice(0, max);
}

function xmlText(value: string): string {
  return value.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").trim();
}

async function searchWeb(query: string) {
  const q = cleanText(query, 220);
  if (!q) return { results: [], note: "Query vuota." };
  const url = "https://www.bing.com/search?" + new URLSearchParams({ format: "rss", q });
  const response = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0 (compatible; CiccioResearch/1.0)" },
    signal: AbortSignal.timeout(12000),
    cache: "no-store"
  });
  if (!response.ok) throw new Error("Ricerca web non disponibile (" + response.status + ").");
  const xml = await response.text();
  const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)].slice(0, 7);
  const results = items.map(match => {
    const block = match[1];
    const title = xmlText((block.match(/<title>([\s\S]*?)<\/title>/i) || [,""])[1]);
    const link = xmlText((block.match(/<link>([\s\S]*?)<\/link>/i) || [,""])[1]);
    const snippet = xmlText((block.match(/<description>([\s\S]*?)<\/description>/i) || [,""])[1]).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    return { title, url: link, snippet };
  }).filter(x => x.title && /^https?:\/\//i.test(x.url));
  return { query: q, results, note: results.length ? "Risultati di ricerca: verifica le pagine originali prima di presentare dati come certi." : "Il motore non ha restituito risultati leggibili." };
}

async function listTasks(c: Config, status?: string) {
  const params = new URLSearchParams({ select: "id,title,status,notes,created_at,updated_at", user_id: "eq." + c.user, order: "created_at.desc", limit: "15" });
  if (status && ["Da fare", "In corso", "Completata", "Bloccata"].includes(status)) params.set("status", "eq." + status);
  const r = await fetch(c.base + "/rest/v1/ciccio_tasks?" + params.toString(), { headers: headers(c), cache: "no-store" });
  if (!r.ok) throw new Error("Lettura attività non riuscita (" + r.status + ").");
  return await r.json() as TaskRow[];
}

async function createTask(c: Config, title: string, notes: string) {
  const safeTitle = cleanText(title, 180);
  if (!safeTitle) throw new Error("Titolo attività obbligatorio.");
  const open = await listTasks(c);
  const norm = (s: string) => s.toLocaleLowerCase("it-IT").replace(/[^a-z0-9àèéìòù]+/g, " ").trim();
  const duplicate = open.find(t => t.status !== "Completata" && t.status !== "Bloccata" && norm(t.title) === norm(safeTitle));
  if (duplicate) return { created: false, duplicate: true, task: duplicate, message: "Esiste già un incarico aperto equivalente." };
  const r = await fetch(c.base + "/rest/v1/ciccio_tasks", {
    method: "POST",
    headers: { ...headers(c), "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify({
      user_id: c.user, title: safeTitle, status: "Da fare",
      notes: cleanText(notes || "Incarico assegnato dalla chat. Eseguire le attività reversibili; nessun contatto esterno, pubblicazione o spesa senza approvazione.", 2800)
    })
  });
  if (!r.ok) throw new Error("Creazione attività non riuscita (" + r.status + ").");
  const rows = await r.json() as TaskRow[];
  if (!rows[0]) throw new Error("Supabase non ha confermato la creazione dell'attività.");
  return { created: true, task: rows[0], message: "Attività creata e verificata nel database." };
}

async function getTask(c: Config, id: string) {
  const params = new URLSearchParams({ select: "id,title,status,notes,created_at,updated_at", id: "eq." + cleanText(id, 80), user_id: "eq." + c.user, limit: "1" });
  const r = await fetch(c.base + "/rest/v1/ciccio_tasks?" + params.toString(), { headers: headers(c), cache: "no-store" });
  if (!r.ok) throw new Error("Lettura incarico non riuscita (" + r.status + ").");
  const rows = await r.json() as TaskRow[];
  return rows[0] || null;
}

async function appendTaskNotes(c: Config, id: string, update: string) {
  const task = await getTask(c, id);
  if (!task) throw new Error("Incarico non trovato per questo utente.");
  const addition = cleanText(update, 1800);
  if (!addition) throw new Error("Aggiornamento vuoto.");
  const next = ((task.notes || "") + "\n\n" + addition).slice(-3000);
  const r = await fetch(c.base + "/rest/v1/ciccio_tasks?id=eq." + encodeURIComponent(id) + "&user_id=eq." + encodeURIComponent(c.user), {
    method: "PATCH",
    headers: { ...headers(c), "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify({ notes: next, updated_at: new Date().toISOString() })
  });
  if (!r.ok) throw new Error("Aggiornamento incarico non riuscito (" + r.status + ").");
  const rows = await r.json() as TaskRow[];
  if (!rows[0]) throw new Error("Aggiornamento non confermato.");
  return { updated: true, task: rows[0] };
}

async function listActivity(c: Config) {
  const params = new URLSearchParams({ select: "created_at,goal,action,status,result,verification", order: "created_at.desc", limit: "8" });
  const r = await fetch(c.base + "/rest/v1/ciccio_agent_runs?" + params.toString(), { headers: headers(c), cache: "no-store" });
  if (!r.ok) throw new Error("Lettura registro attività non riuscita (" + r.status + ").");
  return await r.json();
}

async function saveMemory(c: Config, content: string, kind: string) {
  const value = cleanText(content, 1000);
  if (!value) throw new Error("Contenuto memoria vuoto.");
  await saveRows(c, [{ kind: cleanText(kind || "nota_utente", 40), content: value }]);
  return { saved: true, content: value };
}

const tools = [
  { type: "function", function: { name: "search_web", description: "Cerca sul web informazioni pubbliche e restituisce titolo, URL e snippet. Usa questa funzione per ricerche attuali; non inventare risultati.", parameters: { type: "object", properties: { query: { type: "string" } }, required: ["query"], additionalProperties: false } } },
  { type: "function", function: { name: "list_tasks", description: "Legge gli incarichi dell'utente nella coda Ciccio.", parameters: { type: "object", properties: { status: { type: "string", enum: ["Da fare", "In corso", "Completata", "Bloccata"] } }, additionalProperties: false } } },
  { type: "function", function: { name: "create_task", description: "Crea un incarico che il runner autonomo di Ciccio elaborerà nei suoi cicli.", parameters: { type: "object", properties: { title: { type: "string" }, notes: { type: "string" } }, required: ["title", "notes"], additionalProperties: false } } },
  { type: "function", function: { name: "get_task", description: "Legge un incarico specifico, incluso il suo stato e i risultati salvati.", parameters: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false } } },
  { type: "function", function: { name: "append_task_update", description: "Aggiunge un risultato o una nota verificata a un incarico senza dichiararlo completato.", parameters: { type: "object", properties: { id: { type: "string" }, update: { type: "string" } }, required: ["id", "update"], additionalProperties: false } } },
  { type: "function", function: { name: "list_activity", description: "Legge gli ultimi cicli di lavoro registrati dall'agente Ciccio.", parameters: { type: "object", properties: {}, additionalProperties: false } } },
  { type: "function", function: { name: "save_memory", description: "Salva una preferenza o decisione durevole comunicata dall'utente.", parameters: { type: "object", properties: { content: { type: "string" }, kind: { type: "string" } }, required: ["content"], additionalProperties: false } } }
] as const;

async function executeTool(c: Config, name: string, args: Record<string, unknown>) {
  switch (name) {
    case "search_web": return await searchWeb(String(args.query || ""));
    case "list_tasks": return await listTasks(c, args.status ? String(args.status) : undefined);
    case "create_task": return await createTask(c, String(args.title || ""), String(args.notes || ""));
    case "get_task": return await getTask(c, String(args.id || ""));
    case "append_task_update": return await appendTaskNotes(c, String(args.id || ""), String(args.update || ""));
    case "list_activity": return await listActivity(c);
    case "save_memory": return await saveMemory(c, String(args.content || ""), String(args.kind || "nota_utente"));
    default: throw new Error("Strumento non riconosciuto.");
  }
}

const systemBase = [
  "Sei Ciccio, agente operativo personale dell'utente. Ragioni con lui in italiano naturale e lavori davvero usando gli strumenti disponibili.",
  "Non limitarti a dare istruzioni: quando serve informazione attuale usa search_web; per incarichi che richiedono lavoro successivo usa create_task; per aggiornamenti consulta list_tasks/get_task/list_activity; conserva risultati verificati con append_task_update.",
  "Per una richiesta semplice rispondi direttamente. Per una richiesta di ricerca immediata esegui le ricerche prima di rispondere. Per un progetto che richiede più tempo crea un incarico e spiega che sarà elaborato dal runner automatico; non fingere che sia già finito.",
  "Non inventare fonti, aziende, recapiti, verifiche o progressi. Distingui fatti verificati, snippet di ricerca e ipotesi; quando possibile cita gli URL restituiti dagli strumenti.",
  "Puoi svolgere autonomamente ricerca, analisi, organizzazione, preparazione di documenti e bozze. Non inviare email o messaggi a terzi, non pubblicare, non spendere denaro e non assumere impegni senza approvazione esplicita.",
  "Non creare incarichi duplicati. Prima di creare un incarico verifica la coda con list_tasks.",
  "Quando l'utente chiede cosa stai facendo o cosa hai fatto, controlla i dati reali tramite gli strumenti. Non dichiarare completato un incarico solo perché è stato creato.",
  "Non chiedere 'vuoi che ti aiuti?' quando l'utente ha già dato un incarico. Se un dato essenziale manca, fai una sola domanda mirata.",
  "Memoria utente: "
].join("\n");

export async function GET() {
  if (!await isAuthenticated()) return NextResponse.json({ error: "Non autorizzato" }, { status: 401 });
  try {
    const c = config();
    const rows = (await readMemory(c)).reverse();
    const messages = rows.filter(x => ["conversazione", "risposta_assistente"].includes(x.kind))
      .map(x => ({ role: x.kind === "conversazione" ? "user" : "assistant", content: x.content.replace(/^Utente: /, "") }));
    return NextResponse.json({ messages: messages.slice(-60) });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Errore memoria" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  if (!await isAuthenticated()) return NextResponse.json({ error: "Non autorizzato" }, { status: 401 });
  try {
    const c = config();
    const body = await req.json();
    const message = cleanText(body.message, 8000);
    if (!message) return NextResponse.json({ error: "Il messaggio è vuoto." }, { status: 400 });

    const rows = (await readMemory(c)).reverse();
    const durable = rows.filter(x => !["conversazione", "risposta_assistente"].includes(x.kind)).slice(-8);
    const memoryContext = durable.map(x => "- [" + x.kind + "] " + x.content.slice(0, 260)).join("\n").slice(-2200) || "(nessuna memoria salvata)";
    const recent = rows.filter(x => ["conversazione", "risposta_assistente"].includes(x.kind)).slice(-6)
      .map(x => ({ role: x.kind === "conversazione" ? "user" : "assistant", content: x.content.replace(/^Utente: /, "").slice(-900) }));

    const messages: Array<Record<string, unknown>> = [
      { role: "system", content: systemBase + memoryContext },
      ...recent,
      { role: "user", content: message }
    ];

    let finalReply = "";
    let toolCount = 0;
    for (let round = 0; round < 5; round++) {
      let response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: { Authorization: "Bearer " + c.groq, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "openai/gpt-oss-20b",
          messages,
          tools,
          tool_choice: "auto",
          parallel_tool_calls: false,
          temperature: 0.4,
          max_completion_tokens: 1000
        }),
        signal: AbortSignal.timeout(45000)
      });
      let data = await response.json();
      let activeProvider = "Groq";

      // Automatic free fallback: preserve the same conversation and Ciccio tools.
      if ((response.status === 429 || response.status >= 500) && c.openrouter) {
        const fallbackResponse = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + c.openrouter,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ciccio-ai.vercel.app",
            "X-Title": "Ciccio AI"
          },
          body: JSON.stringify({
            model: "openrouter/free",
            messages,
            tools,
            tool_choice: "auto",
            parallel_tool_calls: false,
            temperature: 0.4,
            max_tokens: 1000
          }),
          signal: AbortSignal.timeout(45000)
        });
        const fallbackData = await fallbackResponse.json();
        if (fallbackResponse.ok) {
          response = fallbackResponse;
          data = fallbackData;
          activeProvider = "OpenRouter";
        } else {
          const fallbackDetail = String(fallbackData?.error?.message || fallbackData?.message || "servizio non disponibile").slice(0, 180);
          return NextResponse.json({
            error: fallbackResponse.status === 429
              ? "Groq ha esaurito la quota e anche il modello gratuito di riserva OpenRouter ha raggiunto il suo limite. Le quote gratuite si ripristinano secondo i limiti del provider. Dettaglio: " + fallbackDetail
              : "Groq non è disponibile e OpenRouter non ha completato la richiesta. Dettaglio: " + fallbackDetail
          }, { status: fallbackResponse.status === 429 ? 429 : 503 });
        }
      }

      if (response.status === 429 && activeProvider === "OpenRouter") {
        return NextResponse.json({ error: "Il modello gratuito di riserva OpenRouter ha raggiunto il limite temporaneo o giornaliero. Riprova più tardi; Ciccio non ha effettuato spese." }, { status: 429 });
      }
      if (response.status === 429) {
        const providerMessage = String(data?.error?.message || "");
        const providerCode = String(data?.error?.code || data?.error?.type || "").toLowerCase();
        const detail = (providerCode + " " + providerMessage).toLowerCase();
        const retryHeader = response.headers.get("retry-after");
        const retrySeconds = retryHeader && /^\\d+$/.test(retryHeader) ? Math.max(1, Number(retryHeader)) : null;
        let userMessage: string;
        if (/insufficient_quota|billing|credits|quota_exceeded|daily.*limit|tokens per day|tpm.*day/.test(detail)) {
          userMessage = "Il credito o il limite giornaliero del servizio AI è esaurito. Aspettare qualche secondo non risolve: bisogna ripristinare la quota oppure passare a un modello/servizio con disponibilità.";
        } else if (/rate_limit|tokens per minute|requests per minute|tpm|rpm/.test(detail)) {
          userMessage = retrySeconds
            ? "Il servizio AI ha raggiunto il limite temporaneo di richieste. Riprova tra circa " + retrySeconds + " secondi."
            : "Il servizio AI ha raggiunto il limite temporaneo di richieste. Attendi un minuto e riprova.";
        } else {
          userMessage = retrySeconds
            ? "Il servizio AI ha rifiutato la richiesta per un limite di utilizzo. Riprova tra circa " + retrySeconds + " secondi."
            : "Il servizio AI ha rifiutato la richiesta per un limite di utilizzo. Non è un blocco della chat: controllare la quota del provider.";
        }
        return NextResponse.json({ error: userMessage, provider_code: providerCode || undefined }, { status: 429, headers: retrySeconds ? { "Retry-After": String(retrySeconds) } : {} });
      }
      if (response.status >= 500) return NextResponse.json({ error: "Il servizio AI è momentaneamente non disponibile. Riprova tra poco." }, { status: 503 });
      if (!response.ok) throw new Error("Modello AI non disponibile (" + response.status + "): " + String(data?.error?.message || "errore provider").slice(0, 220));

      const assistantMessage = data?.choices?.[0]?.message;
      if (!assistantMessage) throw new Error("Il modello non ha restituito una risposta valida.");
      const calls = Array.isArray(assistantMessage.tool_calls) ? assistantMessage.tool_calls : [];
      if (!calls.length) {
        finalReply = String(assistantMessage.content || "").trim();
        break;
      }

      messages.push({ role: "assistant", content: assistantMessage.content || null, tool_calls: calls });
      for (const call of calls) {
        if (toolCount >= 8) {
          messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify({ error: "Limite strumenti per messaggio raggiunto." }) });
          continue;
        }
        toolCount++;
        const name = String(call.function?.name || "");
        let args: Record<string, unknown> = {};
        try {
          args = JSON.parse(String(call.function?.arguments || "{}"));
          const result = await executeTool(c, name, args);
          messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(result).slice(0, 12000) });
        } catch (error) {
          messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify({ error: error instanceof Error ? error.message : "Errore esecuzione strumento" }) });
        }
      }
    }

    if (!finalReply) finalReply = "Ho eseguito gli strumenti disponibili, ma non sono riuscito a comporre la risposta finale. Controlla la coda attività per vedere gli eventuali risultati salvati.";
    await saveRows(c, [
      { kind: "conversazione", content: "Utente: " + message },
      { kind: "risposta_assistente", content: finalReply }
    ]);
    return NextResponse.json({ reply: finalReply, tools_used: toolCount });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Errore durante la conversazione." }, { status: 500 });
  }
}
