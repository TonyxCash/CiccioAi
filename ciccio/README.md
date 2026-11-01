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

## Ricerca clienti — abbigliamento in tutta Italia

Il runner autonomo è orientato alla ricerca di negozi indipendenti di abbigliamento in tutte le regioni italiane, per proporre siti web professionali. Cerca attività reali, verifica le pagine e lo stato del sito, salva fonti e recapiti commerciali pubblici e prepara mini-audit. Non deve chiedere ogni volta una zona o cambiare progetto senza parlarne con l'utente.

**Limiti operativi:** la ricerca usa motori web gratuiti e può essere incompleta o temporaneamente bloccata. Ciccio non invia messaggi, non fa outreach automatico, non apre account, non paga servizi e non dichiara clienti o ricavi senza conferme verificabili. I contatti e i messaggi restano bozze fino a un'autorizzazione esplicita e a un'integrazione appropriata.
