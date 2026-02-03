# Smart_Metal_Factory_Exam_Repository

# Indice dei Contenuti

- [Scenario - Reparto Tornitura Smart](#scenario---reparto-tornitura-smart)
  - [Architettura di Alto Livello & Componenti Principali](#architettura-di-alto-livello--componenti-principali)
  - [Interazioni & Ciclo di Controllo](#interazioni--ciclo-di-controllo)
- [Modelli Dati (Data Models)](#modelli-dati-data-models)
- [Protocolli & Comunicazione](#protocolli--comunicazione)
  - [Mappatura Risorse CoAP](#mappatura-risorse-coap)
  - [Payload SenML + JSON](#payload-senml--json)
- [Strategia di Edge Intelligence](#strategia-di-edge-intelligence)

---

# Scenario - Reparto Tornitura Smart

![Smart Factory Architecture](https://via.placeholder.com/800x400?text=Smart+Factory+Digital+Twin+Architecture)

**Figura 1:** Rappresentazione schematica dello scenario Smart Metal Factory che coinvolge simulazione fisica, esposizione server CoAP e gestione intelligente all'Edge.

Questo progetto implementa una soluzione di **Digital Twin** per una fabbrica metalmeccanica Industria 4.0. Simula un "Reparto Tornitura" suddiviso in isole di produzione. Ogni isola è dotata di macchinari intelligenti che generano dati di telemetria e accettano comandi remoti. Il sistema garantisce monitoraggio in tempo reale, manutenzione automatizzata (es. compattazione rifiuti) e interventi critici di sicurezza (es. svuotamento d'emergenza) tramite un approccio Edge Computing.

---

## Architettura di Alto Livello & Componenti Principali

La soluzione segue un'architettura Cyber-Physical System (CPS) a tre livelli:

- **Livello di Simulazione Fisica (`/model`)**
  - **Waste Bin (Cassone)**: Simula l'accumulo di scarti dai torni. Include una fisica complessa con logica del "pavimento compattato" (i rifiuti diventano più densi e difficili da comprimere nel tempo).
  - **Coolant Tank (Vasca Refrigerante)**: Simula i livelli di torbidità (NTU) che aumentano a causa dei detriti metallici.
  - **Conveyor Belt (Nastro Trasportatore)**: Simula l'accumulo di materiale (kg) sulla linea di produzione.
  - **Attuatori**: Compattatori, Pompe di Filtraggio e Motori che alterano fisicamente i valori dei sensori quando attivati.

- **Livello di Connettività ed Esposizione (`/resources` + `factory_server.py`)**
  - Agisce come **Server CoAP**.
  - Avvolge i modelli fisici in **Risorse CoAP Observable**.
  - Espone un'interfaccia standard (`.well-known/core`) per la discovery dinamica.
  - Esegue un loop fisico a 10Hz per aggiornare gli stati della simulazione e notificare gli osservatori.

- **Livello di Intelligenza Edge (`/client`)**
  - **Smart Waste Manager**: Il "Cervello" del sistema.
  - Esegue la discovery dinamica delle isole e dei dispositivi disponibili.
  - Implementa **Policy di Controllo**:
    - *Policy Soglia*: Attuazione standard (es. accendi compattatore quando cassone > 80%).
    - *Policy Critica*: Reset di emergenza (es. svuota cassone via POST quando > 95%).

## Interazioni & Ciclo di Controllo

1.  **Flusso Telemetria**: I sensori inviano aggiornamenti via CoAP Observe al Manager.
2.  **Processo Decisionale**: Il Manager valuta le policy rispetto ai valori ricevuti.
3.  **Attuazione**:
    - **PUT**: Per operazioni standard (cicli ON/OFF per compattatori/pompe).
    - **POST**: Per reset istantanei (svuotamento cassoni/cambio liquido).

---

# Modelli Dati (Data Models)

Ogni dispositivo fisico è modellato con attributi specifici e logica fisica. I timestamp sono generati all'edge.

**Waste Bin Data Model**
Progettato per la **BinLevelResource**.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `value` | Double | Livello di riempimento percentuale (0.0 - 100.0%) |
| `unit` | String | Unità di misura ("%") |
| `compacted_floor`| Double | Livello minimo di compressione (simula la densità dei rifiuti solidi) |
| `timestamp` | Long | Unix epoch timestamp |

**Coolant Tank Data Model**
Progettato per la **CoolantResource**.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `value` | Double | Livello di torbidità |
| `unit` | String | "NTU" (Nephelometric Turbidity Unit) |
| `timestamp` | Long | Unix epoch timestamp |

**Actuator Status Model**
Usato dalle risorse **Compactor**, **Pump** e **Motor**.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `status` | String | "ON" oppure "OFF" |
| `last_activation`| Long | Unix epoch timestamp dell'ultimo cambio stato |
| `cycle_count` | Integer | (Solo Compattatore) Numero di cicli di compressione eseguiti |

---

# Protocolli & Comunicazione

![CoAP Protocol Diagram](https://via.placeholder.com/800x300?text=CoAP+Request+Response+and+Observe)

**Figura 2:** Pattern di comunicazione utilizzando CoAP (Constrained Application Protocol).

Il progetto utilizza **CoAP** su UDP, scelto per la sua idoneità in ambienti industriali vincolati che richiedono affidabilità e basso overhead.

### Mappatura Risorse CoAP

Il server espone le risorse utilizzando una struttura URI gerarchica:
`coap://<host>:5683/tornitura/<id-isola>/<categoria>/<id-dispositivo>`

| URI Risorsa | Metodi | Scopo |
|--------------|---------|---------|
| `.../waste/bin-1` | GET (Obs), POST | GET per monitorare il livello, POST per svuotare/resettare. |
| `.../waste/compactor-1` | GET, PUT | PUT `{"status": "ON"}` per attivare la pressa. |
| `.../coolant/turbidity-1`| GET (Obs), POST | GET per monitorare torbidità, POST per sostituire liquido. |
| `.../coolant/pump-1` | GET, PUT | PUT `{"status": "ON"}` per attivare filtro. |
| `.../conveyor/weight-1` | GET (Obs) | GET per monitorare il carico (peso). |
| `.../conveyor/motor-1` | GET, PUT | PUT per avviare/fermare il nastro. |

### Payload SenML + JSON

I dati di telemetria utilizzano lo standard JSON **SenML (Sensor Measurement Lists)** per garantire l'interoperabilità.

**Esempio: Aggiornamento Livello Cassone**
```json
[
  {
    "n": "island-1-bin-1",
    "u": "%",
    "v": 85.5,
    "t": 167890000
  }
]
