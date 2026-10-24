# Ciccio AI — prototipo

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
- La chat attuale usa risposte euristiche: non è ancora collegata a un modello linguistico esterno.
- La memoria è SQLite locale. Nei servizi cloud il filesystem può essere effimero: per una memoria persistente usare Supabase/Postgres.
- Nessun processo lavora quando l'app è spenta; l'esecuzione continua richiede un servizio di automazione schedulato.
- Non effettua pagamenti, ordini o azioni esterne.
- Non inserire password, chiavi private, dati bancari o informazioni sensibili.

## Prossimi moduli
1. Collegamento a un modello IA tramite API e chiave segreta lato server.
2. Memoria persistente su Supabase con accesso autenticato.
3. Agente con strumenti limitati, log delle azioni e conferma per operazioni sensibili.
4. Automazioni programmate con limiti di costo e monitoraggio.
