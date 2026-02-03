# How to Start

### Prerequisiti

Assicurarsi di avere Python 3.10+ installato.
Si consiglia di utilizzare un virtual environment.

```bash
# Clona repository
git clone [https://github.com/tuo-username/smart-metal-factory.git](https://github.com/tuo-username/smart-metal-factory.git)
cd smart-metal-factory

# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt


Per il corretto funzionamento, il **Factory Server** deve essere sempre attivo prima di avviare qualsiasi client.

### Step 1: Avviare il Factory Server
Il server simula la fisica dei dispositivi (sensori e attuatori) aggiornando il loro stato a 10Hz.

1.  Apri un terminale.
2.  Naviga nella cartella sorgente ed esegui il server:
    ```bash
    cd src
    python factory_server.py
    ```
3.  **Output atteso:**
    ```text
    >>> Physics Simulation Engine Started (10Hz) <<<
    >>> SMART METAL FACTORY Server Started (Port 5683) <<<
    ```
    > **Nota:** Mantieni questo terminale aperto.

### Step 2: Avviare lo Smart Waste Manager (Autonomous Client)
Questo client esegue la discovery automatica delle risorse e applica le logiche di controllo (es. accende il compattatore se il bidone è pieno).

1.  Apri un **secondo terminale**.
2.  Naviga nella cartella client ed esegui il manager:
    ```bash
    cd src/client
    python smart_waste_manager.py
    ```
3.  **Output atteso:**
    ```text
    --- STARTING SMART WASTE MANAGER ---
    Discovering devices at coap://127.0.0.1:5683...
    [MAPPED] isola-1 > Waste Bin 1 -> coap://127.0.0.1:5683/tornitura/isola-1/waste/bin-1
    ...
    --- CYCLIC MONITORING (Every 1s) ---
       [isola-1] Waste Bin 1: 15.5 % | Rate: +3.50 %/min
    ```

---

## 3. Manual Operations (Test Scripts)

Nella cartella `src/client/` sono presenti script per testare singole operazioni CoAP manualmente. Questi sono utili per il debug o per interagire direttamente con i dispositivi.

**Assicurati di essere nella cartella `src/client/` prima di eseguire i comandi.**

### ➤ GET Request (Lettura Stato)
Legge il valore istantaneo di un sensore o lo stato di un attuatore.

1.  Apri il file `coap_get_client.py`.
2.  Modifica la variabile `URI_PATH` con la risorsa desiderata (es. `"tornitura/isola-1/waste/bin-1"`).
3.  Esegui:
    ```bash
    python coap_get_client.py
    ```

### ➤ PUT Request (Attuazione ON/OFF)
Invia un comando per modificare lo stato di un attuatore (es. Motore, Pompa, Compattatore).

1.  Apri il file `coap_put_client.py`.
2.  Modifica `URI_PATH` puntando a un attuatore (es. `"tornitura/isola-1/conveyor/motor-1"`).
3.  Modifica `CMD_STATUS` impostandolo su `"ON"` o `"OFF"`.
4.  Esegui:
    ```bash
    python coap_put_client.py
    ```

### ➤ POST Request (Reset / Azione)
Esegue un'azione senza stato, come il reset di un sensore (es. svuotamento bidone o cambio liquido).

1.  Apri il file `coap_post_client.py`.
2.  Modifica `URI_PATH` puntando a un sensore che supporta il reset (es. `"tornitura/isola-1/waste/bin-1"`).
3.  Esegui:
    ```bash
    python coap_post_client.py
    ```
    *Effetto:* Il valore del sensore sul server verrà resettato (es. a 0.0 o 5.0).

### ➤ OBSERVE Request (Streaming Dati)
Sottoscrizione a una risorsa per ricevere aggiornamenti in tempo reale (Push) senza fare polling.

1.  Apri il file `coap_obs_get_client.py`.
2.  Modifica `URI_PATH` con la risorsa da monitorare (es. `"tornitura/isola-1/conveyor/weight-1"`).
3.  Esegui:
    ```bash
    python coap_obs_get_client.py
    ```
4.  Per terminare l'osservazione, premi `CTRL+C`.
