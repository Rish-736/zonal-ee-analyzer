import networkx as nx

def get_ecu_zone(data, ecu_id):
    for zone in data['zones']:
        for ecu in zone['ecus']:
            if ecu['id'] == ecu_id:
                return zone['id']
    return None

def get_zone_distance(data, zone_a, zone_b):
    if zone_a == zone_b:
        return 0.5
    distances = data['zone_distances']
    key1 = f"{zone_a.lower()}_to_{zone_b.lower()}"
    key2 = f"{zone_b.lower()}_to_{zone_a.lower()}"
    if key1 in distances:
        return distances[key1]
    elif key2 in distances:
        return distances[key2]
    return 3.0

def build_legacy_graph(data):
    G = nx.Graph()

    for zone in data['zones']:
        for ecu in zone['ecus']:
            G.add_node(ecu['id'], zone=zone['id'], zone_name=zone['name'])

    for conn in data['connections']:
        from_ecu = conn['from']
        to_ecu = conn['to']
        zone_a = get_ecu_zone(data, from_ecu)
        zone_b = get_ecu_zone(data, to_ecu)
        wire_length = get_zone_distance(data, zone_a, zone_b)
        G.add_edge(from_ecu, to_ecu, weight=wire_length, signal=conn['signal'])

    return G

def build_zonal_graph(data):
    G = nx.Graph()

    for zone in data['zones']:
        zc = zone['zone_controller']
        G.add_node(zc, zone=zone['id'], is_controller=True)
        for ecu in zone['ecus']:
            G.add_node(ecu['id'], zone=zone['id'], is_controller=False)
            G.add_edge(ecu['id'], zc, weight=ecu['local_wire_length_m'])

    controllers = [z['zone_controller'] for z in data['zones']]
    backbone_segments = [
        (controllers[0], controllers[1], 3.0),
        (controllers[1], controllers[2], 2.5),
        (controllers[2], controllers[3], 1.5),
    ]
    for a, b, length in backbone_segments:
        G.add_edge(a, b, weight=length, is_backbone=True)

    return G

if __name__ == "__main__":
    from parser import load_truck_config
    data = load_truck_config("configs/cascadia_126_2020.yaml")

    legacy = build_legacy_graph(data)
    zonal = build_zonal_graph(data)

    print(f"Legacy graph  — Nodes: {legacy.number_of_nodes()}, Edges: {legacy.number_of_edges()}")
    print(f"Zonal graph   — Nodes: {zonal.number_of_nodes()},  Edges: {zonal.number_of_edges()}")

    legacy_length = sum(d['weight'] for _, _, d in legacy.edges(data=True))
    zonal_length = sum(d['weight'] for _, _, d in zonal.edges(data=True))

    print(f"Legacy total wire length : {legacy_length:.1f} m")
    print(f"Zonal total wire length  : {zonal_length:.1f} m")