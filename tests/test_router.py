from src.core.router import parse_travel_time_to_minutes, RailRouter


def test_parse_travel_time_to_minutes():
    assert parse_travel_time_to_minutes(150) == 150
    assert parse_travel_time_to_minutes("150") == 150
    assert parse_travel_time_to_minutes("2h 30m") == 150
    assert parse_travel_time_to_minutes("2h30m") == 150
    assert parse_travel_time_to_minutes("2h") == 120
    assert parse_travel_time_to_minutes("45m") == 45
    assert parse_travel_time_to_minutes("2:30") == 150
    assert parse_travel_time_to_minutes("hasta 2 horas y 30 minutos") == 150
    assert parse_travel_time_to_minutes("1 hora y 15 minutos") == 75
    assert parse_travel_time_to_minutes("2.5") == 150


def test_parse_travel_time_edge_cases():
    # Hours followed by bare minutes
    assert parse_travel_time_to_minutes("2h30") == 150
    assert parse_travel_time_to_minutes("2 h 30") == 150
    assert parse_travel_time_to_minutes("1h05") == 65
    # Spanish decimal comma and fractions
    assert parse_travel_time_to_minutes("3,5") == 210
    assert parse_travel_time_to_minutes("1 hora y media") == 90
    assert parse_travel_time_to_minutes("2 horas y cuarto") == 135
    # Numbers behave the same whether given as str, int or float
    assert parse_travel_time_to_minutes(2) == parse_travel_time_to_minutes("2") == 120
    assert parse_travel_time_to_minutes(10.0) == parse_travel_time_to_minutes("10") == 600


def test_station_lookup(router: RailRouter):
    # Test by full name
    st1 = router.find_station("Santiago de Compostela")
    assert st1 is not None
    assert st1.id == "SCQ"

    # Test by alias / city
    st2 = router.find_station("Santiago")
    assert st2 is not None
    assert st2.id == "SCQ"

    # Test case insensitive
    st3 = router.find_station("madrid-atocha")
    assert st3 is not None
    assert st3.id == "MAD_ATO"

    # Non-existent station
    assert router.find_station("Estación Fantasma 12345") is None


def test_reachable_destinations_threshold(router: RailRouter):
    origin = router.find_station("Santiago de Compostela")
    assert origin is not None

    # Within 30 minutes: only A Coruña (28 min), Vilagarcía (20 min) and Padrón (16 min)
    routes_30 = router.find_reachable_destinations(origin=origin, max_duration_minutes=30)
    dest_ids_30 = [r.destination.id for r in routes_30]

    assert "LCG" in dest_ids_30  # A Coruña
    assert "VGA" in dest_ids_30  # Vilagarcía
    assert "PAD" in dest_ids_30  # Padrón
    assert "VGO" not in dest_ids_30  # Vigo takes ~55 min, shouldn't be included

    # All returned routes must be <= 30 min
    for r in routes_30:
        assert r.total_duration_minutes <= 30


def test_reachable_destinations_deduplication(router: RailRouter):
    origin = router.find_station("Santiago de Compostela")
    assert origin is not None

    routes_120 = router.find_reachable_destinations(origin=origin, max_duration_minutes=120)
    dest_ids = [r.destination.id for r in routes_120]

    # Check deduplication: each destination station appears exactly once
    assert len(dest_ids) == len(set(dest_ids))
    assert origin.id not in dest_ids  # Origin should not be in reachable destinations


def test_transfer_routes(router: RailRouter):
    origin = router.find_station("Santiago de Compostela")
    assert origin is not None

    # Monforte de Lemos is reachable via Ourense:
    # Santiago -> Ourense (38 min) + layover (15 min) + Ourense -> Monforte (42 min) = 95 min
    routes = router.find_reachable_destinations(origin=origin, max_duration_minutes=100, allow_transfers=True)
    monforte_route = next((r for r in routes if r.destination.id == "MNF"), None)

    assert monforte_route is not None
    assert not monforte_route.is_direct
    assert monforte_route.transfer_station is not None
    assert monforte_route.transfer_station.id == "OUN"
    assert monforte_route.total_duration_minutes <= 100


def test_valencia_reachability_benicarlo(router: RailRouter):
    origin = router.find_station("Valencia")
    assert origin is not None
    assert origin.id == "VLC"

    # Within 120 minutes (2h), Benicarló-Peñíscola (100 min) must be reachable
    routes_120 = router.find_reachable_destinations(origin=origin, max_duration_minutes=120)
    dest_ids_120 = [r.destination.id for r in routes_120]

    assert "BEN" in dest_ids_120  # Benicarló-Peñíscola
    assert "BCS" in dest_ids_120  # Benicàssim
    assert "CAS" in dest_ids_120  # Castelló de la Plana
    assert "SAG" in dest_ids_120  # Sagunt
    assert "XAT" in dest_ids_120  # Xàtiva
    assert "GAN" in dest_ids_120  # Gandia

    benicarlo_route = next(r for r in routes_120 if r.destination.id == "BEN")
    assert benicarlo_route.is_direct
    assert benicarlo_route.total_duration_minutes == 100


def test_benicarlo_station_lookup(router: RailRouter):
    for q in ["Benicarlo", "Benicarló", "peñiscola", "Peñíscola", "Benicarló-Peñíscola"]:
        st = router.find_station(q)
        assert st is not None, f"Failed lookup for {q}"
        assert st.id == "BEN"


def test_route_cache_invalidated_when_network_changes(rail_provider, temp_cache):
    from src.core.router import RailRouter

    origin = rail_provider.find_station("Santiago de Compostela")
    RailRouter(rail_provider, cache=temp_cache).find_reachable_destinations(origin, 30)

    # Same number of nodes/edges, different durations -> must not reuse cached routes
    for seg in rail_provider._segments:
        if seg.from_station_id == "SCQ" and seg.to_station_id == "LCG":
            seg.duration_minutes = 45
    routes = RailRouter(rail_provider, cache=temp_cache).find_reachable_destinations(origin, 30)
    assert "LCG" not in [r.destination.id for r in routes]
