import hashlib
import re
from typing import Dict, List, Optional
import networkx as nx

from src.config import settings
from src.core.cache import SQLiteCache
from src.core.models import RouteOption, Segment, Station
from src.providers.base import RailDataProvider


_HOURS_AS_NUMBER_LIMIT = 10  # Bare numbers up to this value are read as hours ("2.5" -> 150 min)
_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:horas?|hrs?|h)(?![a-záéíóú])\s*(?:y\s+)?(\d{1,2}(?!\s*(?:\.|\d)))?")
_MINUTES_RE = re.compile(r"(\d+)\s*(?:minutos?|mins?|m)(?![a-záéíóú])")
_FRACTION_WORDS = {"media": 30, "cuarto": 15}


def parse_travel_time_to_minutes(time_input: str | int | float) -> int:
    """
    Parses diverse travel time expressions into total minutes:
    - 150 -> 150
    - "150" -> 150
    - "2h" -> 120
    - "2h 30m" -> 150
    - "2h30" -> 150
    - "2:30" -> 150
    - "2.5" / "2,5" -> 150
    - "hasta 2 horas y 30 minutos" -> 150
    - "1 hora y media" -> 90
    Unparseable input falls back to settings.DEFAULT_MAX_TRAVEL_HOURS.
    """
    if isinstance(time_input, (int, float)):
        # Small numbers are hours (2.5 -> 150), anything bigger is already minutes
        if time_input <= _HOURS_AS_NUMBER_LIMIT:
            return int(round(time_input * 60))
        return int(time_input)

    text = str(time_input).lower().strip().replace(",", ".")

    # "X horas [y] Y [minutos]" / "Xh Ym" / "XhY" / "X hora y media"
    hours_match = _HOURS_RE.search(text)
    mins_match = _MINUTES_RE.search(text)
    if hours_match or mins_match:
        total = 0.0
        if hours_match:
            total += float(hours_match.group(1)) * 60
            if hours_match.group(2):
                total += int(hours_match.group(2))
            elif not mins_match:
                total += next((m for w, m in _FRACTION_WORDS.items() if f"y {w}" in text), 0)
        if mins_match and not (hours_match and hours_match.group(2)):
            total += int(mins_match.group(1))
        return int(round(total))

    # Look for "H:MM" format
    colon_match = re.match(r"^(\d+):(\d{2})$", text)
    if colon_match:
        return int(colon_match.group(1)) * 60 + int(colon_match.group(2))

    # Plain number: "2" or "2.5" are hours, "120" is minutes
    try:
        return parse_travel_time_to_minutes(float(text))
    except ValueError:
        pass

    # Default fallback to config setting
    return int(settings.DEFAULT_MAX_TRAVEL_HOURS * 60)


class RailRouter:
    """
    Graph-based routing engine for Media Distancia rail routes.
    Computes reachable destinations within a travel time threshold,
    supporting both direct routes and single-transfer combinations.
    """

    def __init__(self, rail_provider: RailDataProvider, cache: Optional[SQLiteCache] = None):
        self.rail_provider = rail_provider
        self.cache = cache or SQLiteCache()
        self._graph: Optional[nx.MultiDiGraph] = None
        self._stations: Dict[str, Station] = {}
        self._network_signature = ""
        self._initialize_network()

    def _initialize_network(self) -> None:
        self._stations = {s.id: s for s in self.rail_provider.get_all_stations()}
        self._graph = nx.MultiDiGraph()

        for s_id in self._stations:
            self._graph.add_node(s_id)

        for route_data in self.rail_provider.get_all_segments():
            self._graph.add_edge(
                route_data.from_station_id,
                route_data.to_station_id,
                duration_minutes=route_data.duration_minutes,
                train_type=route_data.train_type,
                frequency_daily=route_data.frequency_daily,
                line=route_data.line,
            )

        # Fingerprint of the network contents, so cached routes are invalidated
        # whenever the data changes (not only when node/edge counts change).
        digest = hashlib.sha1()
        for u, v, d in sorted(self._graph.edges(data=True), key=lambda e: (e[0], e[1], e[2]["duration_minutes"])):
            digest.update(f"{u}>{v}:{d['duration_minutes']}:{d['train_type']}:{d['frequency_daily']};".encode("utf-8"))
        self._network_signature = digest.hexdigest()[:12]

    def find_station(self, query: str) -> Optional[Station]:
        """Resolves station by name, city, code, or alias."""
        return self.rail_provider.find_station(query)

    def find_reachable_destinations(
        self,
        origin: Station,
        max_duration_minutes: int,
        allow_transfers: bool = True,
        transfer_margin_minutes: Optional[int] = None
    ) -> List[RouteOption]:
        """
        Finds all destinations reachable from origin within max_duration_minutes.
        Returns a deduplicated list of RouteOption items (best route per destination).
        """
        margin = (
            transfer_margin_minutes
            if transfer_margin_minutes is not None
            else settings.DEFAULT_MIN_TRANSFER_MARGIN_MINUTES
        )
        cache_key = f"rail:{self._network_signature}:{origin.id}:{max_duration_minutes}:{allow_transfers}:{margin}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return [RouteOption.model_validate(item) for item in cached]

        best_routes_by_destination: Dict[str, RouteOption] = {}

        # 1. DIRECT ROUTES
        for _, dest_id, edge_data in self._graph.out_edges(origin.id, data=True):
            if dest_id == origin.id:
                continue
            dest_station = self._stations.get(dest_id)
            if not dest_station:
                continue

            duration = edge_data["duration_minutes"]
            if duration <= max_duration_minutes:
                # If already recorded a direct route, retain the fastest one
                if dest_id in best_routes_by_destination and duration >= best_routes_by_destination[dest_id].total_duration_minutes:
                    continue

                segment = Segment(
                    from_station_id=origin.id,
                    to_station_id=dest_id,
                    duration_minutes=duration,
                    train_type=edge_data.get("train_type", "Media Distancia"),
                    frequency_daily=edge_data.get("frequency_daily", 6),
                    line=edge_data.get("line"),
                )
                route = RouteOption(
                    origin=origin,
                    destination=dest_station,
                    total_duration_minutes=duration,
                    is_direct=True,
                    segments=[segment],
                    transfer_station=None,
                    transfer_wait_minutes=0,
                    estimated_frequency_daily=segment.frequency_daily,
                )
                best_routes_by_destination[dest_id] = route

        # 2. SINGLE TRANSFER ROUTES (Origin -> Transfer -> Destination)
        if allow_transfers:
            for _, transfer_id, leg1_data in self._graph.out_edges(origin.id, data=True):
                if transfer_id == origin.id:
                    continue
                t1 = leg1_data["duration_minutes"]
                if t1 + margin >= max_duration_minutes:
                    continue

                transfer_station = self._stations.get(transfer_id)
                if not transfer_station:
                    continue

                for _, dest_id, leg2_data in self._graph.out_edges(transfer_id, data=True):
                    if dest_id == origin.id or dest_id == transfer_id:
                        continue
                    dest_station = self._stations.get(dest_id)
                    if not dest_station:
                        continue

                    t2 = leg2_data["duration_minutes"]
                    total_time = t1 + margin + t2

                    if total_time <= max_duration_minutes:
                        seg1 = Segment(
                            from_station_id=origin.id,
                            to_station_id=transfer_id,
                            duration_minutes=t1,
                            train_type=leg1_data.get("train_type", "Media Distancia"),
                            frequency_daily=leg1_data.get("frequency_daily", 6),
                            line=leg1_data.get("line"),
                        )
                        seg2 = Segment(
                            from_station_id=transfer_id,
                            to_station_id=dest_id,
                            duration_minutes=t2,
                            train_type=leg2_data.get("train_type", "Media Distancia"),
                            frequency_daily=leg2_data.get("frequency_daily", 6),
                            line=leg2_data.get("line"),
                        )
                        transfer_route = RouteOption(
                            origin=origin,
                            destination=dest_station,
                            total_duration_minutes=total_time,
                            is_direct=False,
                            segments=[seg1, seg2],
                            transfer_station=transfer_station,
                            transfer_wait_minutes=margin,
                            estimated_frequency_daily=min(seg1.frequency_daily, seg2.frequency_daily),
                        )

                        # Decide whether to keep direct vs transfer
                        if dest_id not in best_routes_by_destination:
                            best_routes_by_destination[dest_id] = transfer_route
                        else:
                            existing = best_routes_by_destination[dest_id]
                            # If existing is transfer and new one is faster, replace
                            if not existing.is_direct and transfer_route.total_duration_minutes < existing.total_duration_minutes:
                                best_routes_by_destination[dest_id] = transfer_route
                            # If existing is direct, we generally prefer direct unless transfer is significantly faster
                            elif existing.is_direct and transfer_route.total_duration_minutes < (existing.total_duration_minutes - 20):
                                best_routes_by_destination[dest_id] = transfer_route

        # Sort results by duration ascending
        sorted_routes = sorted(
            best_routes_by_destination.values(),
            key=lambda r: (r.total_duration_minutes, not r.is_direct, -r.estimated_frequency_daily)
        )

        # Cache results as serialized dicts
        self.cache.set(cache_key, [r.model_dump() for r in sorted_routes])
        return sorted_routes
