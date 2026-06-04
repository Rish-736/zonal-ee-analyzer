import yaml

def load_truck_config(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return data

def print_summary(data):
    meta = data['metadata']
    print("=" * 50)
    print(f"Truck: {meta['truck_model']}")
    print(f"Total ECUs: {meta['total_ecus']}")
    print("=" * 50)

    total_ecus_counted = 0
    for zone in data['zones']:
        ecu_count = len(zone['ecus'])
        total_ecus_counted += ecu_count
        print(f"\nZone: {zone['name']}")
        print(f"  Location: {zone['location']}")
        print(f"  Zone Controller: {zone['zone_controller']}")
        print(f"  ECUs ({ecu_count}):")
        for ecu in zone['ecus']:
            print(f"    - {ecu['id']}: {ecu['name']}")

    print("\n" + "=" * 50)
    print(f"Total connections: {len(data['connections'])}")
    print("Connections:")
    for conn in data['connections']:
        print(f"  {conn['from']} --> {conn['to']}: {conn['signal']}")
    print("=" * 50)
    print(f"\nECUs verified: {total_ecus_counted} (metadata says {meta['total_ecus']})")

if __name__ == "__main__":
    config = load_truck_config("configs/cascadia_126_2020.yaml")
    print_summary(config)