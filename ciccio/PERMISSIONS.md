# Ciccio — autorizzazioni e autonomia

Questo documento distingue le capacità abilitate dal codice dai permessi che richiedono configurazione dell'account.

## Capacità previste nei cicli automatici
- Avvio programmato tramite GitHub Actions ogni 6 ore e avvio manuale.
- Uso del modello Groq configurato in `GROQ_API_KEY`.
- Ricerca su pagine web pubbliche tramite il motore di ricerca implementato nel runner.
- Lettura/scrittura di attività, memorie e registro Ciccio in Supabase.
- Creazione di deliverable testuali, verifica del loro salvataggio e registrazione dell'esito.
- Invio di resoconti all'indirizzo configurato e, se configurato, notifiche Telegram.

## Secrets richiesti in GitHub Actions
Configurare in **Settings → Secrets and variables → Actions**. I valori devono restare segreti e non vanno mai incollati in chat o nel repository.

Obbligatori:
- `GROQ_API_KEY`: chiave API Groq valida con quota disponibile.
- `SUPABASE_PROJECT_URL`: URL del progetto Supabase.
- `SUPABASE_SERVICE_ROLE_KEY`: chiave server-side Supabase; non esporla mai nel frontend o nel repository.
- `CICCIO_USER_ID`: UUID reale dell'utente Supabase Auth.

Per le notifiche email:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM`.

Opzionali:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## Secrets dell'app Streamlit
Per condividere le stesse attività e memorie con il runner, configurare i valori server-side:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CICCIO_USER_ID`
- `GROQ_API_KEY`
- `CICCIO_APP_PASSWORD` (password d'accesso all'app se viene usata la service-role key).

I valori di GitHub e Streamlit vanno configurati separatamente. Il codice non può leggere né verificare direttamente i valori nascosti nelle impostazioni degli account.

## Livelli di autonomia
### Può eseguire nei limiti del codice e dei secrets
Ricercare, analizzare, creare bozze e deliverable, organizzare attività, salvare risultati, verificare i record e inviare resoconti all'utente.

### Richiede strumenti e test aggiuntivi prima di dichiararla attiva
- Monitoraggio affidabile di opportunità e clienti su più siti.
- Esportazione di deliverable in formati diversi dal testo.
- Integrazioni con marketplace o piattaforme di lavoro.
- Gestione di richieste, consegne, revisioni e stato dei pagamenti.

### Deve restare dietro approvazione esplicita dell'utente
Inviare messaggi a potenziali clienti, pubblicare offerte o contenuti, accettare contratti, creare account a nome dell'utente, acquistare servizi, spendere denaro, accedere a conti finanziari o trasferire fondi/cripto. Non memorizzare password, codici OTP, seed phrase o chiavi private.

## Verifica prima di dichiarare Ciccio operativo
1. Controllare che tutti i secrets obbligatori esistano in GitHub Actions e Streamlit.
2. Controllare che `CICCIO_USER_ID` sia l'UUID dell'utente corretto in Supabase Auth.
3. Verificare che lo schema `ciccio/agent_schema.sql` sia stato eseguito nel progetto Supabase usato dall'app e dal workflow.
4. Eseguire il workflow manualmente e verificare log, riga `ciccio_agent_runs`, attività/memorie e notifica.
5. Verificare il deploy Streamlit e il download dei deliverable.

**Importante:** un ciclo completato significa che il lavoro tecnico è stato salvato e verificato. Non dimostra da solo che il servizio sia richiesto, che un cliente compri o che siano stati incassati soldi.
