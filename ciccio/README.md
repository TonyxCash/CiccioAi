# Ciccio AI — dashboard legacy

Agente personale in italiano per organizzare conversazioni, memoria di lavoro, attività e movimenti economici.

## Avvio
Da una cartella Python:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Distribuzione
Per una distribuzione Streamlit Community Cloud, seleziona questo repository e imposta **Main file path** su `ciccio/app.py`. Il file delle dipendenze è `ciccio/requirements.txt`.

## Stato e limiti
- La chat principale è la web app Next.js su https://ciccio-ai.vercel.app; questo modulo Streamlit è una dashboard precedente.
- La memoria è SQLite locale. Nei servizi cloud il filesystem può essere effimero: per una memoria persistente usare Supabase/Postgres.
- Nessun processo lavora quando l'app è spenta; l'esecuzione continua richiede un servizio di automazione schedulato.
- Non effettua pagamenti, ordini o azioni esterne.
- Non inserire password, chiavi private, dati bancari o informazioni sensibili.

## Prossimi moduli
1. Collegamento a un modello IA tramite API e chiave segreta lato server.
2. Memoria persistente su Supabase con accesso autenticato.
3. Agente con strumenti limitati, log delle azioni e conferma per operazioni sensibili.
4. Automazioni programmate con limiti di costo e monitoraggio.

## Ricerca clienti — tutta Italia

Il runner cerca negozi indipendenti di abbigliamento e boutique, ristoranti e pizzerie in tutte le regioni italiane. Ruota comuni e settori, raccoglie schede e recapiti commerciali pubblici, individua il sito indicato dall'attività e ne verifica direttamente la pagina prima di descriverlo come sito ufficiale.

### Google Places (facoltativo)

Per abilitare la ricerca strutturata su Google Maps:
1. Crea un progetto in Google Cloud Console.
2. Abilita Places API (New) e configura la fatturazione e le quote.
3. Crea una API key con restrizioni appropriate.
4. Aggiungi la chiave nei GitHub Actions secrets con il nome `GOOGLE_MAPS_API_KEY`.

Senza la chiave, Ciccio continua a usare motori di ricerca web e OpenStreetMap. Google Places viene interrogato per un settore e un gruppo di comuni per ciclo, con rotazione dei settori (abbigliamento, ristoranti, pizzerie) per contenere le richieste. Google Places può comportare costi in base al piano, ai campi richiesti e all'utilizzo: controllare prezzi e quote in Google Cloud prima di abilitarlo.

**Limiti operativi:** una scheda Google o OSM è un candidato da verificare, non prova da sola che l'attività sia ancora aperta o interessata a un sito. L'assenza di un sito nei risultati non prova che l'attività ne sia priva. Ciccio non invia messaggi né contatta automaticamente i negozi: prepara lead, prove, mini-audit e bozze per la revisione dell'utente.
