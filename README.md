# Ciccio AI

Ciccio è un collaboratore AI personale in italiano. La chat principale è una web app Next.js, con memoria persistente su Supabase e un agente operativo schedulato tramite GitHub Actions.

## Accesso

- App: https://ciccio-ai.vercel.app
- Repository: https://github.com/TonyxCash/CiccioAi
- Progetto Vercel: `ciccio-ai`
- Database: Supabase

## Obiettivo operativo attuale

Trovare e acquisire clienti per la vendita di siti web professionali a negozi indipendenti di abbigliamento in **tutta Italia**, non soltanto in Campania.

Ciccio deve:
1. Cercare attività reali in più regioni italiane.
2. Aprire le pagine delle attività e verificare le informazioni.
3. Cercare il sito ufficiale del negozio e controllarlo direttamente.
4. Distinguere con prove: `ASSENTE`, `ESISTENTE`, `DA MIGLIORARE` o `NON VERIFICATO`.
5. Salvare nome, città, provincia, fonti, sito e recapiti commerciali pubblicati.
6. Preparare mini-audit, demo e proposte concrete.

Non deve chiedere ogni volta settore o zona. Non deve cambiare progetto senza parlarne con l'utente.

## Come funziona

- `app/`: chat Next.js e API server.
- `lib/session.ts`: sessione privata della chat.
- `ciccio/agent_runner.py`: agente che esegue i lavori salvati.
- `ciccio/artifacts.py`: salvataggio dei deliverable.
- `ciccio/agent_schema.sql`: schema del database.
- `.github/workflows/ciccio-agent.yml`: esecuzione automatica.
- `ciccio/test_*.py`: test automatici.

La chat usa Groq come modello principale e OpenRouter come riserva gratuita quando configurato. Le ricerche web usano motori pubblici gratuiti; disponibilità e qualità dei risultati possono variare.

## Automazione

GitHub Actions esegue Ciccio tre volte al giorno (07:17, 13:17 e 19:17 UTC) e consente anche l'avvio manuale. Non è un processo attivo 24 ore su 24: GitHub può ritardare gli orari programmati.

Ogni ciclo:
- legge incarichi e memorie;
- dà priorità agli incarichi di ricerca clienti per siti web;
- raccoglie e controlla fonti pubbliche;
- salva il risultato e un file scaricabile;
- registra esito e verifiche in Supabase.

## Regole di sicurezza

- Nessun contatto a potenziali clienti senza approvazione.
- Nessuna pubblicazione o spesa senza approvazione.
- Nessun pagamento o trasferimento di denaro.
- Nessun dato inventato: l'assenza di risultati di ricerca non dimostra che un negozio non abbia un sito.
- Le chiavi segrete restano nei Secrets di GitHub e nelle variabili server-side di Vercel; mai nel codice o nel browser.

## Configurazione

### Vercel
Variabili server-side richieste:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CICCIO_USER_ID`
- `CICCIO_APP_PASSWORD`
- `CICCIO_SESSION_SECRET` (almeno 32 caratteri)
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY` (facoltativa)

### GitHub Actions
Secrets richiesti:
- `GROQ_API_KEY`
- `SUPABASE_PROJECT_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CICCIO_USER_ID`

Notifiche email e Telegram sono facoltative. Non copiare mai le chiavi in file pubblici.

## Verifiche

Prima di considerare una modifica pronta:
1. compilare i file;
2. eseguire i test automatici;
3. controllare il risultato del workflow;
4. verificare lo stato della distribuzione Vercel;
5. controllare gli errori runtime.

La sola presenza di un commit o di un workflow non dimostra che un'attività sia stata completata.
