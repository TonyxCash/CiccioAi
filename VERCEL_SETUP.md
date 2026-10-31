# Ciccio Web — deploy Vercel

Questa prima versione aggiunge una chat web separata dall'agente automatico GitHub Actions. La chat usa Groq per le risposte e Supabase per recuperare/salvare la memoria condivisa.

## Deploy
1. Importa il repository `TonyxCash/CiccioAi` in Vercel.
2. Framework: Next.js; Root Directory: `./`.
3. Aggiungi le variabili d'ambiente:
   - `GROQ_API_KEY`: la chiave Groq già usata da Ciccio.
   - `SUPABASE_URL`: URL del progetto Supabase.
   - `SUPABASE_SERVICE_ROLE_KEY`: service-role key Supabase. Solo lato server, mai nel browser.
   - `CICCIO_USER_ID`: UUID già usato dal workflow GitHub Actions.
   - `CICCIO_APP_PASSWORD`: password robusta per la chat web.
   - `CICCIO_SESSION_SECRET`: stringa casuale di almeno 32 caratteri per firmare i cookie.
4. Deploy. Apri il dominio Vercel e accedi con `CICCIO_APP_PASSWORD`.

## Memoria condivisa
La chat usa la tabella `public.ciccio_memories` già prevista nello schema dell'agente. Verifica che esista la colonna `user_id` e che il valore di `CICCIO_USER_ID` sia lo stesso UUID usato nelle GitHub Actions.

## Limiti e sicurezza
- La password è un accesso condiviso per una sola persona, non un sistema multiutente.
- Le chiamate al modello AI dipendono dalla quota del provider.
- La chat funziona quando la pagina è aperta; il ciclo autonomo rimane su GitHub Actions.
- Le funzioni Vercel hanno durata limitata: non usarle come processo permanente 24/7.
- Non esporre mai le variabili segrete al client.
- Ciccio non effettua pagamenti, non contatta persone e non pubblica senza approvazione.
