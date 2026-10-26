# ListingAI

Assistente web per venditori di abbigliamento: genera titoli, descrizioni e hashtag, salva annunci in un catalogo temporaneo ed esporta testo e CSV.

## Demo locale

Richiede Python 3.10 o superiore.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy gratuito su Streamlit Community Cloud

1. Apri https://share.streamlit.io/
2. Collega GitHub e scegli il repository `TonyxCash/ListingAI`.
3. Branch: `main`; file principale: `app.py`.
4. Premi Deploy.

## MVP attuale

- Interfaccia responsive e dashboard.
- Generazione di titolo, descrizione e hashtag con modelli locali inclusi.
- Inserimento di categoria, marca, taglia, colore, condizioni, materiale, dettagli e prezzo.
- Esportazione dell'annuncio in TXT e del catalogo in CSV.
- Catalogo conservato solo nella sessione corrente.

## Limiti importanti

- Non c'è ancora login né separazione degli account.
- I dati in sessione non sono un archivio permanente e possono perdersi al riavvio.
- Non pubblica direttamente su marketplace e non usa API a pagamento.
- I suggerimenti non sono una valutazione automatica del mercato; controllare sempre ogni annuncio.
- Non raccogliere o inserire credenziali dei marketplace.

## Roadmap

1. Testare il flusso con venditori reali e raccogliere feedback.
2. Aggiungere database persistente e account in modo sicuro.
3. Validare interesse e disponibilità a pagare prima di integrare abbonamenti.
4. Integrare un provider di pagamenti e gestione abbonamenti solo dopo la validazione.


## Ciccio — agente autonomo

Ciccio es un agente separado de la demo ListingAI. Su ciclo è eseguito da GitHub Actions ogni sei ore e può essere avviato manualmente dalla scheda **Actions**.

### Funzioni implementate

- Legge attività e memorie dell'utente da Supabase.
- Sceglie una singola azione interna e limitata per ciclo.
- Genera risultati concreti per le attività aperte e li salva nelle note dell'attività e in Memorie.
- Verifica la chiusura delle attività prima di considerarle completate.
- Ritenta fino a tre volte le chiamate Groq e le letture Supabase in caso di errori temporanei riconosciuti.
- Registra i fallimenti in `ciccio_agent_runs` quando Supabase è raggiungibile e prova a inviare una notifica email.
- Esegue test automatici di sicurezza prima di avviare il ciclo.

### Configurazione richiesta

Nel repository GitHub, in **Settings → Secrets and variables → Actions**, configura i secret usati dal workflow: `GROQ_API_KEY`, `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY` e `CICCIO_USER_ID`. Per le notifiche sono facoltativi `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM`, `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. Email e Telegram inviano solo riepiloghi al destinatario/chat configurati; un errore di notifica non annulla un'azione già salvata.

Esegui lo schema SQL di `ciccio/agent_schema.sql` nel progetto Supabase prima del primo ciclo. Non mettere mai chiavi segrete nel codice o in file pubblici.

### Limiti e sicurezza

Ciccio può operare autonomamente sulle proprie attività e memorie. Non pubblica annunci, non contatta persone, non spende denaro e non modifica repository o account esterni. Queste azioni richiedono un'integrazione dedicata e un controllo esplicito. La riuscita va confermata tramite i log di GitHub Actions e i record in Supabase; la presenza del workflow da sola non dimostra che il ciclo sia riuscito.


## Licenza

Prototipo in sviluppo. Aggiungere una licenza prima di distribuire il codice a terzi.
