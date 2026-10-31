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

## Opportunity Lab — motore di ricerca opportunità

Il runner autonomo esplora una sequenza di 10 modelli indipendenti, senza vincolarsi a un settore o ai progetti precedenti dell'utente: ricerca clienti B2B, assistenza virtuale, appuntamenti, sourcing, microservizi digitali, prodotti digitali, monitoraggio prezzi, supporto e-commerce, monitoraggio bandi e affiliazioni.

Per ogni modello crea un esperimento con evidenze pubbliche, requisiti e modalità di pagamento per un operatore residente in Italia, costi iniziali, un campione vendibile e bozze di contatto. Le attività richiedono fonti concrete; lead ipotetici e directory generiche non sono considerati clienti verificati. Dopo i dieci test l'agente produce una revisione comparativa basata sui risultati disponibili.

**Limiti operativi:** la ricerca usa motori web gratuiti e può essere incompleta o temporaneamente bloccata. Ciccio non invia messaggi, non fa outreach automatico, non apre account, non paga servizi e non dichiara clienti o ricavi senza conferme verificabili. I contatti e i messaggi restano bozze fino a un'autorizzazione esplicita e a un'integrazione appropriata.
