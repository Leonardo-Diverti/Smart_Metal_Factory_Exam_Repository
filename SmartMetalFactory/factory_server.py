import logging
import asyncio
import aiocoap.resource as resource
import aiocoap
from resources.bin_level_resource import BinLevelResource
from resources.compactor_resource import CompactorResource
from resources.coolant_resource import CoolantResource
from resources.filter_pump_resource import FilterPumpResource
from resources.conveyor_weight_resource import ConveyorWeightResource
from resources.conveyor_motor_resource import ConveyorMotorResource

logging.basicConfig(level=logging.INFO)
logging.getLogger("coap-server").setLevel(logging.INFO) #imposta logger do aiocoap a livello INFO per richieste in arrivo

#configurazione unica topologia della fabbrica
FACTORY_CONFIG = [
    {"dept": "tornitura", "island": "isola-1", "config": {'bin': 3, 'coolant': 2, 'conveyor': 1}},
    {"dept": "tornitura", "island": "isola-2", "config": {'bin': 1, 'coolant': 2, 'conveyor': 3}},
    # Puoi aggiungere altre isole qui...
]

ALL_RESOURCES = [] #lista risorse di dispotivi che variano nel tempo

def register_bin_chain(root, dept, island, index): #coppia cassone-compattatore ed esposta sulla rete, root è il server coap, dept è repartp
    suffix = f"-{index}"
    #nomi interni di cassone e compattatore con suffissi di isola e fornitura
    r_bin = BinLevelResource(f"{island}-bin{suffix}")
    r_compactor = CompactorResource(f"{island}-compactor{suffix}")

    r_bin.sensor.linked_actuator = r_compactor.actuator #collego attuatore a paramentro del sensore dedicato a link con attuatore
    ALL_RESOURCES.append(r_bin)

    # Esposizione CoAP
    root.add_resource([dept, island, 'waste', f'bin{suffix}'], r_bin)
    root.add_resource([dept, island, 'waste', f'compactor{suffix}'], r_compactor)

def register_coolant_chain(root, dept, island, index):
    suffix = f"-{index}"
    r_turbidity = CoolantResource(f"{island}-coolant{suffix}")
    r_pump = FilterPumpResource(f"{island}-pump{suffix}")
    
    r_turbidity.sensor.linked_actuator = r_pump.actuator
    ALL_RESOURCES.append(r_turbidity)

    root.add_resource([dept, island, 'coolant', f'turbidity{suffix}'], r_turbidity)
    root.add_resource([dept, island, 'coolant', f'pump{suffix}'], r_pump)

def register_conveyor_chain(root, dept, island, index):
    suffix = f"-{index}"
    r_weight = ConveyorWeightResource(f"{island}-conveyor{suffix}")
    r_motor = ConveyorMotorResource(f"{island}-motor{suffix}")
    
    r_weight.sensor.linked_actuator = r_motor.actuator
    ALL_RESOURCES.append(r_weight)

    root.add_resource([dept, island, 'conveyor', f'weight{suffix}'], r_weight)
    root.add_resource([dept, island, 'conveyor', f'motor{suffix}'], r_motor)

def register_island(root, entry):
    dept = entry['dept']
    island = entry['island']
    config = entry['config']
    
    print(f"--- Configuring {dept} > {island} ---")
    
    for i in range(1, config.get('bin', 0) + 1):
        register_bin_chain(root, dept, island, i)
        
    for i in range(1, config.get('coolant', 0) + 1):
        register_coolant_chain(root, dept, island, i)
        
    for i in range(1, config.get('conveyor', 0) + 1):
        register_conveyor_chain(root, dept, island, i)

async def physics_simulation_loop():
    print(">>> Physics Simulation Engine Started (10Hz) <<<")
    while True:
        for res in ALL_RESOURCES:
            # discrmininazione sensore in base a metodo e aggiorna variabili interne
            if hasattr(res.sensor, 'measure_level'): res.sensor.measure_level()
            elif hasattr(res.sensor, 'measure_turbidity'): res.sensor.measure_turbidity()
            elif hasattr(res.sensor, 'measure_weight'): res.sensor.measure_weight()
            
            res.updated_state()  # Notifica aiocoap che lo stato della riorsa corrente è cambiato
        await asyncio.sleep(0.1) #fisica aggiornata 10 volte al secondo 

async def start_server_services(root):
    await aiocoap.Context.create_server_context(root, bind=('127.0.0.1', 5683)) #avvia server coap
    await physics_simulation_loop() # avvia simulazione fisica

def main():
    root = resource.Site()
    # Discovery Endpoint
    root.add_resource(['.well-known', 'core'], resource.WKCResource(root.get_resources_as_linkheader, impl_info=None))

    # Costruzione Dinamica basata sulla CONFIGURAZIONE UNICA
    for entry in FACTORY_CONFIG:
        register_island(root, entry)
    
    print(">>> SMART METAL FACTORY Server Started (Port 5683) <<<")
    try:
        asyncio.run(start_server_services(root))
    except KeyboardInterrupt:
        print("\nServer Stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()