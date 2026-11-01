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
  const base = c.base + "/rest/v1/ciccio_memories?select=created_at,kind,content&user_id=eq." + encodeURIComponent(c.user);
  const [recentResponse, pinnedResponse] = await Promise.all([
    fetch(base + "&order=created_at.desc&limit=40", { headers: headers(c), cache: "no-store" }),
    fetch(base + "&kind=in.(obiettivo_principale,istruzioni_comportamento)&order=created_at.desc&limit=12", { headers: headers(c), cache: "no-store" })
  ]);
  if (!recentResponse.ok || !pinnedResponse.ok) throw new Error("Lettura memoria non riuscita.");
  const recent = await recentResponse.json() as MemoryRow[];
  const pinned = await pinnedResponse.json() as MemoryRow[];
  const unique = new Map<string, MemoryRow>();
  for (const row of [...recent, ...pinned]) unique.set(row.created_at + "|" + row.kind + "|" + row.content, row);
  return [...unique.values()].sort((a, b) => a.created_at.localeCompare(b.created_at));
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

async function inspectPage(rawUrl: string) {
  const value = cleanText(rawUrl, 1200);
  let url: URL;
  try { url = new URL(value); } catch { throw new Error("Indirizzo della pagina non valido."); }
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("Posso aprire soltanto pagine web pubbliche.");
  const host = url.hostname.toLowerCase();
  if (host === "localhost" || host.endsWith(".local") || host === "127.0.0.1" || host === "::1" ||
      /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/.test(host)) {
    throw new Error("Indirizzo privato non consentito.");
  }
  if (host.includes(":") || /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) throw new Error("Indirizzi IP diretti non consentiti.");
  const response = await fetch(url.toString(), {
    headers: { "User-Agent": "Mozilla/5.0 (compatible; CiccioResearch/1.0)" },
    signal: AbortSignal.timeout(10000),
    redirect: "manual",
    cache: "no-store"
  });
  if (response.status >= 300 && response.status < 400) {
    return { url: response.url, status: response.status, title: "", text: "La pagina reindirizza a un altro indirizzo; va verificato separatamente." };
  }
  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) return { url: response.url, status: response.status, title: "", text: "Pagina non raggiungibile con stato HTTP " + response.status };
  if (!contentType.includes("text/html") && !contentType.includes("text/plain")) {
    return { url: response.url, status: response.status, title: "", text: "La pagina non contiene testo HTML leggibile (" + contentType + ")." };
  }
  const html = (await response.text()).slice(0, 500000);
  const title = ((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [,""])[1] || "").replace(/<[^>]*>/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/\s+/g, " ").trim();
  const text = html.replace(/<(script|style|noscript|svg)[^>]*>[\s\S]*?<\/\1>/gi, " ")
    .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&")
    .replace(/&#39;|&apos;/g, "'").replace(/&quot;/g, '"')
    .replace(/\s+/g, " ").trim().slice(0, 5000);
  return { url: response.url, status: response.status, title, text };
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
  { type: "function", function: { name: "search_web", description: "Cerca sul web. Per negozi di abbigliamento cerca in tutta Italia e in più regioni, non chiedere una zona. Restituisce risultati reali ma gli snippet non sono prove: apri le pagine interessanti con inspect_page.", parameters: { type: "object", properties: { query: { type: "string" } }, required: ["query"], additionalProperties: false } } },
  { type: "function", function: { name: "inspect_page", description: "Visita una pagina pubblica già trovata, ne legge titolo e testo visibile e restituisce lo stato HTTP. Usala per verificare negozio, città, sito ufficiale e difetti osservabili. Non dichiara che un sito manca solo perché non lo trova.", parameters: { type: "object", properties: { url: { type: "string" } }, required: ["url"], additionalProperties: false } } },
  { type: "function", function: { name: "list_tasks", description: "Legge gli incarichi dell'utente nella coda Ciccio.", parameters: { type: "object", properties: { status: { type: "string", enum: ["Da fare", "In corso", "Completata", "Bloccata"] } }, additionalProperties: false } } },
  { type: "function", function: { name: "create_task", description: "Crea un incarico che il runner autonomo di Ciccio elaborerà nei suoi cicli.", parameters: { type: "object", properties: { title: { type: "string" }, notes: { type: "string" } }, required: ["title", "notes"], additionalProperties: false } } },
  { type: "function", function: { name: "get_task", description: "Legge un incarico specifico, incluso il suo stato e i risultati salvati.", parameters: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false } } },
  { type: "function", function: { name: "append_task_update", description: "Aggiunge un risultato o una nota verificata a un incarico senza dichiararlo completato.", parameters: { type: "object", properties: { id: { type: "string" }, update: { type: "string" } }, required: ["id", "update"], additionalProperties: false } } },
  { type: "function", function: { name: "list_activity", description: "Legge gli ultimi cicli di lavoro registrati dall'agente Ciccio.", parameters: { type: "object", properties: {}, additionalProperties: false } } },
  { type: "function", function: { name: "save_memory", description: "Salva una preferenza o decisione durevole comunicata dall'utente.", parameters: { type: "object", properties: { content: { type: "string" }, kind: { type: "string" } }, required: ["content"], additionalProperties: false } } }
] as const;

function plainToolSummary(items: Array<{ name: string; result: unknown }>): string {
  const lines: string[] = [];
  for (const item of items) {
    const value = item.result as any;
    if (item.name === "search_web" && value && Array.isArray(value.results)) {
      lines.push("Ho cercato: " + String(value.query || "informazioni richieste") + ".");
      for (const hit of value.results.slice(0, 5)) {
        lines.push("- " + String(hit.title || "Risultato") + (hit.snippet ? ": " + String(hit.snippet).slice(0, 260) : "") + (hit.url ? " — " + String(hit.url) : ""));
      }
      if (!value.results.length) lines.push("La ricerca non ha restituito risultati leggibili.");
    } else if (item.name === "list_tasks" && Array.isArray(value)) {
      lines.push(value.length ? "Nella coda risultano " + value.length + " incarichi:" : "La coda degli incarichi è vuota.");
      for (const task of value.slice(0, 8)) lines.push("- " + task.title + " — " + task.status + (task.notes ? ". " + String(task.notes).slice(0, 220) : ""));
    } else if (item.name === "list_activity" && Array.isArray(value)) {
      lines.push(value.length ? "Ho controllato gli ultimi cicli di lavoro:" : "Non risultano cicli di lavoro registrati.");
      for (const run of value.slice(0, 5)) lines.push("- " + String(run.goal || run.action || "Attività") + " — " + String(run.status || "stato non indicato") + (run.result ? ": " + String(run.result).slice(0, 240) : ""));
    } else if (item.name === "create_task" && value) {
      lines.push(value.created ? "Ho creato l'incarico: " + String(value.task?.title || "") + ". Stato: " + String(value.task?.status || "Da fare") + "." : String(value.message || "L'incarico esiste già.") + (value.task?.title ? " Titolo: " + value.task.title + "." : ""));
    } else if (item.name === "get_task" && value) {
      lines.push(value.title ? "Incarico: " + value.title + ". Stato: " + value.status + ". " + String(value.notes || "").slice(0, 500) : "Non ho trovato l'incarico richiesto.");
    } else if (item.name === "append_task_update" && value) {
      lines.push(value.updated ? "Ho salvato l'aggiornamento all'incarico " + String(value.task?.title || "") + "." : "Non sono riuscito a confermare il salvataggio dell'aggiornamento.");
    } else if (item.name === "save_memory" && value) {
      lines.push(value.saved ? "Ho salvato in memoria: " + String(value.content || "") : "Non ho potuto confermare il salvataggio in memoria.");
    } else if (value?.error) {
      lines.push("Durante " + item.name + " si è verificato un problema: " + String(value.error));
    }
  }
  return lines.length
    ? "Ho completato queste operazioni. Ecco cosa è emerso:\n\n" + lines.join("\n")
    : "Ho avviato alcune operazioni, ma non ho risultati verificabili da comunicarti. Non voglio inventare progressi.";
}

async function executeTool(c: Config, name: string, args: Record<string, unknown>) {
  switch (name) {
    case "search_web": return await searchWeb(String(args.query || ""));
    case "inspect_page": return await inspectPage(String(args.url || ""));
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
  "Sei Ciccio, collaboratore operativo personale dell'utente. Parla in italiano naturale, caldo e diretto, come una persona che ragiona insieme a lui: mai come un manuale, un help desk o un catalogo di funzioni.",
  "Non elencare spontaneamente strumenti, nomi di funzioni, dettagli tecnici o procedure interne. Gli strumenti sono mezzi invisibili: usali per ottenere risultati, non raccontarli.",
  "Quando l'utente esprime un obiettivo, comprendilo, individua il prossimo passo sensato e agisci subito sulle attività reversibili. Non chiedere quale strumento usare e non proporre un menu di opzioni se la richiesta è già chiara.",
  "Obiettivo stabile: vendere siti web professionali a piccole imprese italiane. Priorità attuale: negozi indipendenti di abbigliamento in TUTTA ITALIA. Se l'utente dice 'abbigliamento', 'continua' o 'cerca clienti', applica questo contesto senza chiedere settore o zona. Cerca negozi reali, visita le pagine, verifica se esiste un sito ufficiale e documenta difetti concreti. Distingui sempre siti assenti, esistenti e non verificati. Non spacciare directory e social per siti ufficiali.",
  "Parla come un socio: frasi naturali, brevi e specifiche. Evita formule da call center come 'vuoi provare un termine diverso?', 'potresti indicarmi', 'ecco dove siamo', elenchi di capacità e domande che scaricano il lavoro sull'utente. Se puoi fare un passo, fallo.",
  "Per la ricerca di negozi italiani, fai più ricerche con città e regioni diverse (Milano, Roma, Torino, Bologna, Firenze, Verona, Bari, Palermo, Catania, Napoli e altre). Apri i risultati rilevanti con inspect_page; non fermarti al primo risultato o a una ricerca generica.",
  "Se l'utente vuole ragionare su un progetto, contribuisci con idee, valutazioni, priorità e decisioni motivate. Non limitarti a dire che puoi aiutare: fai avanzare concretamente il lavoro.",
  "Le istruzioni comportamentali e le preferenze permanenti presenti nella memoria hanno priorità sulle indicazioni generiche qui sotto. Evita risposte prolisse e tabelle non necessarie.",
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
    const priorityMemory = rows.filter(x => ["obiettivo_principale", "istruzioni_comportamento"].includes(x.kind)).slice(-6);
    const otherDurable = rows.filter(x => !["conversazione", "risposta_assistente", "obiettivo_principale", "istruzioni_comportamento"].includes(x.kind)).slice(-4);
    const durable = [...otherDurable, ...priorityMemory];
    const memoryContext = durable.map(x => "- [" + x.kind + "] " + x.content.slice(0, 1100)).join("\n").slice(-3200) || "(nessuna memoria salvata)";
    const recent = rows.filter(x => ["conversazione", "risposta_assistente"].includes(x.kind)).slice(-6)
      .map(x => ({ role: x.kind === "conversazione" ? "user" : "assistant", content: x.content.replace(/^Utente: /, "").slice(-900) }));

    const messages: Array<Record<string, unknown>> = [
      { role: "system", content: systemBase + memoryContext },
      ...recent,
      { role: "user", content: message }
    ];

    let finalReply = "";
    let toolCount = 0;
    const toolResults: Array<{ name: string; result: unknown }> = [];
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
        const retrySeconds = retryHeader && /^\d+$/.test(retryHeader) ? Math.max(1, Number(retryHeader)) : null;
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
          toolResults.push({ name, result });
          messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(result).slice(0, 12000) });
        } catch (error) {
          const failure = { error: error instanceof Error ? error.message : "Errore esecuzione strumento" };
          toolResults.push({ name, result: failure });
          messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(failure) });
        }
      }
    }

    // If the tool loop used all rounds, make one final synthesis call with tools disabled.
    // This prevents exposing an internal orchestration failure to the user.
    if (!finalReply) {
      const synthesisMessages = [
        ...messages,
        {
          role: "system",
          content: "Ora concludi la risposta all'utente usando ESCLUSIVAMENTE i risultati degli strumenti già presenti nella conversazione. Non chiamare altri strumenti. Scrivi in italiano naturale, in prima persona, con tono collaborativo e concreto. Non parlare di tool, cicli, limiti interni o errori di composizione. Se hai creato un incarico, comunica titolo e stato reale; se hai trovato dati, riassumili; se un'azione non è riuscita, dillo chiaramente senza inventare. Rispondi direttamente all'obiettivo dell'utente."
        }
      ];
      let synthesisResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: { Authorization: "Bearer " + c.groq, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "openai/gpt-oss-20b",
          messages: synthesisMessages,
          tool_choice: "none",
          temperature: 0.3,
          max_completion_tokens: 900
        }),
        signal: AbortSignal.timeout(45000)
      });
      let synthesisData = await synthesisResponse.json();
      if (!synthesisResponse.ok && c.openrouter) {
        const backup = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + c.openrouter,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ciccio-ai.vercel.app",
            "X-Title": "Ciccio AI"
          },
          body: JSON.stringify({
            model: "openrouter/free",
            messages: synthesisMessages,
            tool_choice: "none",
            temperature: 0.3,
            max_tokens: 900
          }),
          signal: AbortSignal.timeout(45000)
        });
        const backupData = await backup.json();
        if (backup.ok) {
          synthesisResponse = backup;
          synthesisData = backupData;
        }
      }
      if (synthesisResponse.ok) {
        finalReply = String(synthesisData?.choices?.[0]?.message?.content || "").trim();
      }
    }

    if (!finalReply) finalReply = toolCount
      ? plainToolSummary(toolResults)
      : "Non sono riuscito a ottenere una risposta dal servizio AI. Riprova tra poco.";
    await saveRows(c, [
      { kind: "conversazione", content: "Utente: " + message },
      { kind: "risposta_assistente", content: finalReply }
    ]);
    return NextResponse.json({ reply: finalReply, tools_used: toolCount });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Errore durante la conversazione." }, { status: 500 });
  }
}
