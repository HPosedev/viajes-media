import zipfile
from src.core.router import RailRouter
from src.providers.rail.gtfs_provider import GTFSRailProvider

FEED = {
    "stops.txt": (
        "stop_id,stop_name,stop_lat,stop_lon,parent_station\n"
        "A,Alfa,40.0,-3.0,\n"
        "A1,Alfa - Andén 1,40.0,-3.0,A\n"
        "B,Beta,40.1,-3.1,\n"
        "C,Gamma-Centro,40.2,-3.2,\n"
    ),
    "routes.txt": "route_id,route_short_name,route_long_name\nR1,MD,Alfa - Gamma\n",
    "trips.txt": "route_id,service_id,trip_id\nR1,S1,T1\nR1,S2,T2\nR1,S1,T3\n",
    "stop_times.txt": (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        # T1: A1 -> B -> C, departs 08:00
        "T1,08:00:00,08:00:00,A1,1\n"
        "T1,08:40:00,08:42:00,B,2\n"
        "T1,09:30:00,09:30:00,C,3\n"
        # T2: same timetable on another service day (must not double the frequency)
        "T2,08:00:00,08:00:00,A1,1\n"
        "T2,08:40:00,08:42:00,B,2\n"
        "T2,09:30:00,09:30:00,C,3\n"
        # T3: faster A -> C, departs 18:00
        "T3,18:00:00,18:00:00,A,1\n"
        "T3,19:15:00,19:15:00,C,2\n"
    ),
}


def _write_feed(folder):
    folder.mkdir()
    for name, content in FEED.items():
        (folder / name).write_text(content, encoding="utf-8")
    return folder


def test_gtfs_builds_stations_and_segments_from_directory(tmp_path):
    provider = GTFSRailProvider(gtfs_path=_write_feed(tmp_path / "feed"))

    station_ids = {s.id for s in provider.get_all_stations()}
    assert station_ids == {"A", "B", "C"}  # platform A1 is merged into its parent station

    segments = {(s.from_station_id, s.to_station_id): s for s in provider.get_all_segments()}
    assert set(segments) == {("A", "B"), ("A", "C"), ("B", "C")}
    assert segments[("A", "B")].duration_minutes == 40
    assert segments[("A", "C")].duration_minutes == 75  # fastest trip wins
    assert segments[("A", "C")].frequency_daily == 2  # 08:00 and 18:00
    assert segments[("A", "B")].frequency_daily == 1  # same clock time on two service days
    assert segments[("A", "C")].train_type == "Media Distancia"
    assert provider.find_station("gamma").id == "C"


def test_gtfs_zip_feed_is_routable(tmp_path, temp_cache):
    zip_path = tmp_path / "feed.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for name, content in FEED.items():
            z.writestr(name, content)

    provider = GTFSRailProvider(gtfs_path=zip_path)
    router = RailRouter(rail_provider=provider, cache=temp_cache)
    routes = router.find_reachable_destinations(provider.find_station("Alfa"), max_duration_minutes=80)
    assert {r.destination.id for r in routes} == {"B", "C"}


def test_gtfs_without_trips_falls_back_to_seed_network(tmp_path):
    folder = tmp_path / "stops_only"
    folder.mkdir()
    (folder / "stops.txt").write_text(FEED["stops.txt"], encoding="utf-8")

    provider = GTFSRailProvider(gtfs_path=folder)
    # Mixing GTFS stops with seed segments would leave the graph unroutable
    assert "SCQ" in {st.id for st in provider.get_all_stations()}
    assert "A" not in {st.id for st in provider.get_all_stations()}
    assert len(provider.get_all_segments()) > 0
