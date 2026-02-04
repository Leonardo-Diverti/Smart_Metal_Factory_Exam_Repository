import logging
import asyncio
import json
import link_header
from aiocoap import *
from smart_factory_data_model import SmartDevice, FactoryLocation, ControlPolicy

#definisce come appaiono messaggi su console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

#costanti risorse
RT_BIN = "it.unimore.device.sensor.bin_level"
RT_COMPACTOR = "it.unimore.device.actuator.compactor"
RT_TURBIDITY = "it.unimore.device.sensor.coolant_turbidity"
RT_PUMP = "it.unimore.device.actuator.filter_pump"
RT_WEIGHT = "it.unimore.device.sensor.conveyor_weight"
RT_MOTOR = "it.unimore.device.actuator.conveyor_motor"

TARGET = 'coap://127.0.0.1:5683'
WELL_KNOWN = "/.well-known/core"

class SmartWasteManager: #legge i dati sulla rete e applica politiche di controllo
    def __init__(self):
        self.context = None
        self.locations = [] # Lista vuota, verrà popolata dalla discovery

    def get_or_create_location(self, dept_name, island_name):
        #Cerca se l'isola esiste già nel modello locale, altrimenti la crea
        for loc in self.locations:
            if loc.island_name == island_name and loc.department == dept_name:
                return loc
        
        # Se non esiste, la creo
        new_loc = FactoryLocation(dept_name, island_name)
            
        self.locations.append(new_loc)
        print(f"[NEW ISLAND] Detected: {dept_name} / {island_name}")
        return new_loc

    async def discovery_phase(self):
        #Scansiona la rete e costruisce la topologia dinamicamente
        self.context = await Context.create_client_context()
        try:
            print(f"Discovering devices at {TARGET}...")
            req = Message(code=GET, uri=TARGET + WELL_KNOWN) #request a .well-knwn/core
            resp = await self.context.request(req).response #attendo risporta
            links = link_header.parse(resp.payload.decode('utf-8')).links #risposta in link format che viene tradotto da link header in oggetti facili da leggere
            
            for link in links:
                if 'rt' not in dict(link.attr_pairs): continue
                #viene estratto resource type e uri
                found_rt = dict(link.attr_pairs)['rt']
                href = link.href # es: /tornitura/isola-1/waste/bin-1
                full_uri = TARGET + href
                
                #estraggo reparto, isola e id dispositivo da uri per costruire modello dinamico
                parts = href.strip('/').split('/') #
                
                # Controllo validità percorso
                if len(parts) < 4: continue 
                
                #assegno parti a variabili per get_or_create_location
                dept = parts[0]   # tornitura
                island = parts[1] # isola-1
                # type = parts[2]  # indice 2 -> "waste" (Non lo usiamo, ma sappiamo che c'è)
                dev_id_str = parts[3] # bin-1
                
                # Ottengo o creo l'isola
                loc = self.get_or_create_location(dept, island)
                
                
                #creazione sensori e attuatori
                
                # CASO 1: È un Sensore -> Creo SmartDevice e assegno Policy
                if "sensor" in found_rt:
                    # Controllo se l'ho già aggiunto per evitare duplicati
                    if any(d.uri == full_uri for d in loc.devices): continue

                    new_dev = None
                    
                    if found_rt == RT_BIN:
                        # Ho trovato un bidone -> Configuro come Bidone
                        new_dev = SmartDevice(f"Waste Bin {dev_id_str}", RT_BIN, "%")
                        # Assegno Policy Dinamicamente
                        p_norm = ControlPolicy(80.0, 5.0, RT_COMPACTOR, "PUT")
                        p_crit = ControlPolicy(95.0, 0.0, RT_BIN, "POST")
                        new_dev.set_policy(p_norm)
                        new_dev.set_critical_policy(p_crit)

                    elif found_rt == RT_TURBIDITY:
                        new_dev = SmartDevice(f"Coolant Tank {dev_id_str}", RT_TURBIDITY, "NTU")
                        p_pol = ControlPolicy(15.0, 4.0, RT_PUMP, "PUT")
                        new_dev.set_policy(p_pol)

                    elif found_rt == RT_WEIGHT:
                        new_dev = SmartDevice(f"Conveyor {dev_id_str}", RT_WEIGHT, "kg")
                        p_pol = ControlPolicy(150.0, 3.0, RT_MOTOR, "PUT")
                        new_dev.set_policy(p_pol)
                    
                    if new_dev:
                        new_dev.uri = full_uri
                        new_dev.internal_id = dev_id_str
                        loc.add_device(new_dev)
                        print(f"[MAPPED] {loc.island_name} > {new_dev.name} -> {full_uri}")

                # CASO 2: È un Attuatore -> Mappo nella rubrica dell'isola
                elif "actuator" in found_rt:
                    # Estraggo il numero ID (es. "1" da "motor-1") per associarlo al sensore "1"
                    try:
                        idx_suffix = dev_id_str.split('-')[-1] 
                        key = f"{found_rt}-{idx_suffix}"
                        loc.actuator_map[key] = full_uri
                        # print(f"[ACTUATOR] Mapped {key} for {loc.island_name}")
                    except: pass

        except Exception as e:
            print(f"Discovery Error: {e}")

    async def execute_policy(self, device, loc, policy):
        target_uri = None

        #caso A: il target è lo stesso tipo di risorsa del dispositivo (es. svuotamento cassone)
        if policy.target_rt == device.resource_type:
            target_uri = device.uri
        #caso B: il target è un attuatore collegato al proprio sensore
        elif hasattr(loc, "actuator_map"):
            dev_idx = device.internal_id.split('-')[-1]
            lookup_key = f"{policy.target_rt}-{dev_idx}"
            target_uri = loc.actuator_map.get(lookup_key)
        
        if not target_uri: 
            # logging.warning(f"Target not found for policy on {device.name}")
            return

        device.actuation_in_progress = True #segna che l'attuatore è acceso e di non riattivarlo di nuovo finché non finisce 
        try:
            #metodi che si possono applicare ad attuatore attivo
            if policy.method == "POST":
                logging.warning(f"[{loc.island_name}] !!! CRITICAL {device.name} ({device.value:.1f}{device.unit}). RESET (POST)...")
                req = Message(code=POST, uri=target_uri)
                await self.context.request(req).response
                logging.info(f"   -> [{loc.island_name}] {device.name}: FULLY EMPTIED.")

            elif policy.method == "PUT":
                logging.warning(f"[{loc.island_name}] !!! THRESHOLD {device.name} ({device.value:.1f}{device.unit}). ACTIVATION...")
                req_on = Message(code=PUT, uri=target_uri, payload=json.dumps({"status": "ON"}).encode('utf-8'))
                await self.context.request(req_on).response
                
                await asyncio.sleep(policy.restore_time)
                
                req_off = Message(code=PUT, uri=target_uri, payload=json.dumps({"status": "OFF"}).encode('utf-8'))
                await self.context.request(req_off).response
                logging.info(f"   -> [{loc.island_name}] {device.name}: RESTORED (OFF)")

        except Exception as e:
            logging.error(f"Policy Error: {e}")
        finally:
            device.actuation_in_progress = False

    async def run(self):
        print("--- STARTING SMART WASTE MANAGER (DYNAMIC) ---")
        await self.discovery_phase() #scoperta risorse CoAP in rete 

        if not self.locations:
            print("No islands found! Is the factory server running?")
            return

        while True:
            print(f"\n--- CYCLIC MONITORING ({len(self.locations)} Islands found) ---")
            for loc in self.locations:
                for device in loc.devices:
                    if not device.uri: continue
                    try:
                        req = Message(code=GET, uri=device.uri)
                        resp = await self.context.request(req).response 
                        data = json.loads(resp.payload.decode('utf-8'))
                        
                        
                        if isinstance(data, list) and len(data) > 0:  #format SenML se dato è una lista quindi è di un sensore
                            val = data[0].get('v', 0) 
                        else: 
                            val = float(data.get('v', 0)) # altrimenti fa parte del dizionario (attuatori) e prende solo valore v
                        
                        device.update_value(val) #riempie il valore nel dispostivo virtuale (sensore o attuatore che sia)
                        rate = device.calculate_efficiency_rate()
                        
                        print(f"   [{loc.island_name}] {device.name}: {val:.1f} {device.unit} | Rate: {rate:+.2f} {device.unit}/min")

                        if not device.actuation_in_progress: #se l'atttuatore non è già in funzione attiva le policy di controllo
                            if device.critical_policy and val >= device.critical_policy.threshold:
                                asyncio.create_task(self.execute_policy(device, loc, device.critical_policy))
                            elif device.policy and val > device.policy.threshold:
                                asyncio.create_task(self.execute_policy(device, loc, device.policy))
                                
                    except Exception as e:
                        logging.error(f"Read Error {device.name}: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    manager = SmartWasteManager()
    asyncio.run(manager.run())