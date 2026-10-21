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

## Licenza

Prototipo in sviluppo. Aggiungere una licenza prima di distribuire il codice a terzi.
