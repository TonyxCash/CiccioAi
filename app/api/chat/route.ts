import { NextRequest,NextResponse } from "next/server";
import { isAuthenticated } from "@/lib/session";
export const runtime="nodejs";export const dynamic="force-dynamic";
function config(){const base=(process.env.SUPABASE_URL||"").replace(/\/$/,"");const key=process.env.SUPABASE_SERVICE_ROLE_KEY||"";const user=process.env.CICCIO_USER_ID||"";const groq=process.env.GROQ_API_KEY||"";if(!base||!key||!user||!groq)throw new Error("Mancano SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CICCIO_USER_ID o GROQ_API_KEY nelle variabili Vercel.");return {base,key,user,groq};}
function authHeaders(c:ReturnType<typeof config>){return {"apikey":c.key,"Authorization":"Bearer "+c.key};}
async function memory(c:ReturnType<typeof config>){const url=c.base+"/rest/v1/ciccio_memories?select=created_at,kind,content&user_id=eq."+encodeURIComponent(c.user)+"&order=created_at.desc&limit=30";const r=await fetch(url,{headers:authHeaders(c),cache:"no-store"});if(!r.ok)throw new Error("Non riesco a leggere la memoria Supabase ("+r.status+").");return await r.json() as Array<{created_at:string;kind:string;content:string}>;}
async function save(c:ReturnType<typeof config>,items:Array<{kind:string;content:string}>){const r=await fetch(c.base+"/rest/v1/ciccio_memories",{method:"POST",headers:{...authHeaders(c),"Content-Type":"application/json","Prefer":"return=minimal"},body:JSON.stringify(items.map(x=>({...x,user_id:c.user})))});if(!r.ok)throw new Error("Non riesco a salvare la conversazione in Supabase ("+r.status+").");}
export async function GET(){if(!await isAuthenticated())return NextResponse.json({error:"Non autorizzato"},{status:401});try{const c=config();const rows=(await memory(c)).reverse();const messages=rows.filter(x=>["conversazione","risposta_assistente"].includes(x.kind)).map(x=>({role:x.kind==="conversazione"?"user":"assistant",content:x.content.replace(/^Utente: /,"")}));return NextResponse.json({messages:messages.slice(-60)});}catch(e){return NextResponse.json({error:e instanceof Error?e.message:"Errore memoria"},{status:500});}}
export async function POST(req:NextRequest){if(!await isAuthenticated())return NextResponse.json({error:"Non autorizzato"},{status:401});try{const c=config();const body=await req.json();const message=String(body.message||"").trim();if(!message||message.length>8000)return NextResponse.json({error:"Il messaggio è vuoto o troppo lungo."},{status:400});const rows=(await memory(c)).reverse();const durable=rows.filter(x=>!["conversazione","risposta_assistente"].includes(x.kind)).slice(-4);let context=durable.map(x=>"- ["+x.kind+"] "+String(x.content).slice(0,220)).join("\n").slice(-1200);if(!context)context="(nessuna memoria salvata)";const recent=rows.filter(x=>["conversazione","risposta_assistente"].includes(x.kind)).slice(-4).map(x=>({role:x.kind==="conversazione"?"user":"assistant",content:String(x.content).replace(/^Utente: /,"").slice(-350)}));const systemPrompt = [
"Sei Ciccio, un agente operativo personale che lavora per l'utente. Non sei un chatbot informativo, un consulente che si limita a dare consigli o un generatore di idee.",
"MISSIONE: trasformare gli obiettivi assegnati in lavoro concreto, portarlo avanti usando i processi e gli strumenti realmente disponibili nel progetto, conservare i risultati e riferire ciò che hai effettivamente fatto.",
"",
"COMPORTAMENTO OPERATIVO:",
"- Quando l'utente assegna un'attività, considerala un incarico: non chiedere se vuole che tu lo aiuti, non proporre di scrivere un modello perché lo faccia lui e non scaricare su di lui la ricerca, la preparazione o l'organizzazione che puoi svolgere.",
"- Non rispondere con formule come 'vuoi che ti aiuti?', 'puoi fare così', 'ti consiglio di', 'ecco i passaggi che dovresti seguire' quando l'utente ti ha chiesto di eseguire il lavoro.",
"- Scomponi l'incarico in risultati verificabili, usa la coda attività condivisa e il ciclo autonomo programmato per eseguirlo. Dai priorità alle attività aperte già assegnate dall'utente; non creare duplicati.",
"- Lavora in autonomia sui compiti reversibili e a basso rischio: ricerca, verifica fonti, analisi, creazione di documenti, portfolio, pagine demo, bozze commerciali, organizzazione lead e report.",
"- Se un'attività richiede un servizio esterno, credenziali non configurate, una decisione commerciale o un'azione irreversibile, completa tutto ciò che puoi e chiedi soltanto l'autorizzazione o il dato strettamente necessario per il passaggio bloccato.",
"- Non inviare email, DM o messaggi a potenziali clienti, non pubblicare, non spendere denaro e non assumere impegni a nome dell'utente senza autorizzazione esplicita. Puoi però preparare i messaggi e la lista destinatari.",
"- Non dichiarare di aver avviato, completato o verificato un'attività se non è realmente accaduto. Distingui sempre tra fatto, tentativo e prossimo passo.",
"- Se il lavoro è in coda o verrà svolto dal ciclo automatico, dillo chiaramente e indica quale attività è stata presa in carico; non fingere che sia già completata.",
"- Quando il lavoro è finito, consegna il risultato in chat/dashboard e usa la notifica email configurata. Se è parziale, mostra ciò che è stato verificato e continua senza inventare dati.",
"",
"STILE:",
"- Italiano naturale, diretto e collaborativo, come un dipendente competente che aggiorna il proprio responsabile.",
"- Breve nelle conversazioni normali; dettagliato quando consegni un lavoro.",
"- Non fare domande inutili e non chiedere all'utente di ripetere informazioni già disponibili.",
"- Esprimi giudizi sinceri e segnala rischi o limiti senza abbandonare l'incarico.",
"- Non promettere guadagni o risultati certi.",
"",
"MEMORIA DISPONIBILE:",
context||"(nessuna memoria salvata)"
].join("\n");
const actionable = /\\b(trova|cerca|ricerca|prepara|crea|realizza|costruisci|sviluppa|analizza|verifica|organizza|avvia|procedi|occupati|fai|genera|scrivi|progetta|individua)\\b/i.test(message) && message.length >= 18;
let queuedTask: {id:string;title:string}|null = null;
if (actionable) {
  const taskTitle = message.replace(/\\s+/g," ").trim().slice(0,180);
  const taskUrl = c.base + "/rest/v1/ciccio_tasks?select=id,title,status,notes&user_id=eq." + encodeURIComponent(c.user) + "&status=in.(Da%20fare,In%20corso)&order=created_at.desc&limit=20";
  const openResponse = await fetch(taskUrl,{headers:authHeaders(c),cache:"no-store"});
  if (!openResponse.ok) throw new Error("Non riesco a controllare la coda attività ("+openResponse.status+").");
  const openTasks = await openResponse.json() as Array<{id:string;title:string;status:string;notes:string}>;
  const normalized = taskTitle.toLocaleLowerCase("it-IT").replace(/[^a-z0-9àèéìòù]+/g," ").trim();
  const existing = openTasks.find(t => {
    const prior = String(t.title||"").toLocaleLowerCase("it-IT").replace(/[^a-z0-9àèéìòù]+/g," ").trim();
    return prior === normalized || (prior.length > 35 && normalized.length > 35 && (prior.includes(normalized.slice(0,65)) || normalized.includes(prior.slice(0,65))));
  });
  if (existing) queuedTask = {id:existing.id,title:existing.title};
  else {
    const createResponse = await fetch(c.base + "/rest/v1/ciccio_tasks",{method:"POST",headers:{...authHeaders(c),"Content-Type":"application/json","Prefer":"return=representation"},body:JSON.stringify({user_id:c.user,title:taskTitle,status:"Da fare",notes:"Incarico assegnato dalla chat Ciccio.\nRichiesta originale: "+message+"\nEseguire in autonomia tutte le attività reversibili e verificabili. Non contattare terzi, pubblicare o spendere denaro senza autorizzazione esplicita."})});
    if (!createResponse.ok) throw new Error("Non riesco ad aggiungere l'incarico alla coda Ciccio ("+createResponse.status+").");
    const created = await createResponse.json() as Array<{id:string;title:string}>;
    if (created[0]) queuedTask = {id:created[0].id,title:created[0].title};
  }
}
const taskInstruction = queuedTask ? "INCARICO REGISTRATO NELLA CODA CON ID "+queuedTask.id+" E TITOLO: "+queuedTask.title+". La coda è elaborata dal runner automatico. Conferma solo che è stato preso in carico, non dire che il lavoro è già stato svolto." : "";
const messages=[{role:"system",content:systemPrompt+"\\n\\n"+taskInstruction},...recent,{role:"user",content:message}];const response=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Authorization":"Bearer "+c.groq,"Content-Type":"application/json"},body:JSON.stringify({model:"openai/gpt-oss-20b",messages,temperature:0.6,max_completion_tokens:550})});const data=await response.json();if(response.status===429){const rawRetry=response.headers.get("retry-after")||"10";const retrySeconds=/^\\d+$/.test(rawRetry)?rawRetry:"10";return NextResponse.json({error:"Ciccio è momentaneamente occupato. Riprova tra "+retrySeconds+" secondi."},{status:429,headers:{"Retry-After":retrySeconds}});}if(response.status>=500){return NextResponse.json({error:"Il servizio AI è momentaneamente non disponibile. Riprova tra poco."},{status:503});}if(!response.ok)throw new Error("Il modello AI non è disponibile ("+response.status+"): "+String(data?.error?.message||"errore provider").slice(0,220));const reply=String(data?.choices?.[0]?.message?.content||"Non sono riuscito a formulare una risposta.");await save(c,[{kind:"conversazione",content:"Utente: "+message},{kind:"risposta_assistente",content:reply}]);return NextResponse.json({reply});}catch(e){return NextResponse.json({error:e instanceof Error?e.message:"Errore durante la conversazione."},{status:500});}}
