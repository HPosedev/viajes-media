from collections import defaultdict
import csv
import io
import logging
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple
import zipfile

from src.core.models import Segment, Station
from src.providers.base import RailDataProvider
from src.providers.rail.local_graph import LocalGraphRailProvider

logger = logging.getLogger(__name__)

# Common Renfe route_short_name codes -> readable train type
TRAIN_TYPE_NAMES: Dict[str, str] = {
    "MD": "Media Distancia",
    "REG": "Regional",
    "REG.EXP.": "Regional Express",
    "REGEXP": "Regional Express",
    "AVANT": "Avant",
    "AVE": "AVE",
    "ALVIA": "Alvia",
    "INTERCITY": "Intercity",
    "FEVE": "Feve",
}

# Opens a GTFS file by name (e.g. "stops.txt") or returns None when it is missing
FileOpener = Callable[[str], Optional[io.TextIOBase]]


def _parse_gtfs_time(value: str) -> Optional[int]:
    """Parses GTFS 'HH:MM:SS' (hours may exceed 24) into seconds since service-day start."""
    parts = (value or "").strip().split(":")
    if len(parts) != 3:
        return None
    try:
        h, m, s = (int(p) for p in parts)
    except ValueError:
        return None
    return h * 3600 + m * 60 + s


class GTFSRailProvider(RailDataProvider):
    """
    Ingests and parses standard GTFS rail transit feeds (e.g. Renfe Open Data or MITMA NAP).

    Every pair of stops (A before B) served by the same trip becomes a direct Segment A -> B,
    keeping the fastest duration and counting distinct departure times as the daily frequency.
    Falls back to LocalGraphRailProvider if the GTFS source is missing, unreadable or empty.
    """

    def __init__(self, gtfs_path: Optional[Path] = None, fallback_provider: Optional[RailDataProvider] = None):
        self.gtfs_path = gtfs_path
        self.fallback_provider = fallback_provider or LocalGraphRailProvider()
        self._stations: Dict[str, Station] = {}
        self._segments: List[Segment] = []
        self._loaded_gtfs = False

        if self.gtfs_path and self.gtfs_path.exists():
            self._load_gtfs()
        else:
            logger.info("No GTFS source found at %s. Using local seed rail provider.", self.gtfs_path)

    def _load_gtfs(self) -> None:
        """Parses stops, routes, trips and stop_times from a GTFS folder or zip archive."""
        try:
            if self.gtfs_path.is_file() and self.gtfs_path.suffix == ".zip":
                with zipfile.ZipFile(self.gtfs_path, "r") as z:
                    names = set(z.namelist())

                    def open_zip(name: str) -> Optional[io.TextIOBase]:
                        if name not in names:
                            return None
                        return io.TextIOWrapper(z.open(name), encoding="utf-8-sig")

                    self._parse_feed(open_zip)
            elif self.gtfs_path.is_dir():
                def open_dir(name: str) -> Optional[io.TextIOBase]:
                    path = self.gtfs_path / name
                    return open(path, mode="r", encoding="utf-8-sig") if path.exists() else None

                self._parse_feed(open_dir)
            else:
                raise ValueError("GTFS path must be a .zip file or a directory")

            if not self._stations or not self._segments:
                raise ValueError("feed contains no usable stations or trips")

            self._loaded_gtfs = True
            logger.info("Loaded %d stations and %d segments from GTFS.", len(self._stations), len(self._segments))
        except Exception as e:
            logger.error("Failed to parse GTFS: %s. Reverting to fallback.", e)
            self._stations = {}
            self._segments = []
            self._loaded_gtfs = False

    @staticmethod
    def _read_rows(opener: FileOpener, name: str) -> Iterator[Dict[str, str]]:
        f = opener(name)
        if f is None:
            return
        with f:
            for row in csv.DictReader(f):
                yield {k.strip(): (v or "").strip() for k, v in row.items() if k}

    def _parse_feed(self, opener: FileOpener) -> None:
        stop_to_station = self._parse_stops(opener)
        trip_info = self._parse_trips(opener)
        self._segments = self._build_segments(opener, stop_to_station, trip_info)

    def _parse_stops(self, opener: FileOpener) -> Dict[str, str]:
        """Creates Stations and returns a map stop_id -> station id (platforms map to their parent station)."""
        rows = list(self._read_rows(opener, "stops.txt"))
        known_ids = {r.get("stop_id") for r in rows}
        stop_to_station: Dict[str, str] = {}

        for row in rows:
            s_id = row.get("stop_id", "")
            s_name = row.get("stop_name", "")
            if not s_id or not s_name:
                continue
            parent = row.get("parent_station", "")
            if parent and parent in known_ids:
                stop_to_station[s_id] = parent
                continue
            stop_to_station[s_id] = s_id
            self._stations[s_id] = Station(
                id=s_id,
                name=s_name,
                city=s_name.split("-")[0].strip(),
                province="",
                autonomous_community="",
                lat=float(row.get("stop_lat") or 0.0),
                lon=float(row.get("stop_lon") or 0.0),
                aliases=[s_name],
            )
        return stop_to_station

    def _parse_trips(self, opener: FileOpener) -> Dict[str, Tuple[str, Optional[str]]]:
        """Returns trip_id -> (train_type, line name)."""
        routes: Dict[str, Tuple[str, Optional[str]]] = {}
        for row in self._read_rows(opener, "routes.txt"):
            short = row.get("route_short_name", "")
            long_name = row.get("route_long_name", "") or None
            train_type = TRAIN_TYPE_NAMES.get(short.upper(), short) or "Media Distancia"
            routes[row.get("route_id", "")] = (train_type, long_name)

        default = ("Media Distancia", None)
        return {
            row["trip_id"]: routes.get(row.get("route_id", ""), default)
            for row in self._read_rows(opener, "trips.txt")
            if row.get("trip_id")
        }

    def _build_segments(
        self,
        opener: FileOpener,
        stop_to_station: Dict[str, str],
        trip_info: Dict[str, Tuple[str, Optional[str]]],
    ) -> List[Segment]:
        # trip_id -> [(stop_sequence, station_id, arrival_s, departure_s)]
        trips: Dict[str, List[Tuple[int, str, Optional[int], Optional[int]]]] = defaultdict(list)
        for row in self._read_rows(opener, "stop_times.txt"):
            station_id = stop_to_station.get(row.get("stop_id", ""))
            if not station_id:
                continue
            try:
                seq = int(row.get("stop_sequence", ""))
            except ValueError:
                continue
            trips[row.get("trip_id", "")].append(
                (seq, station_id, _parse_gtfs_time(row.get("arrival_time", "")), _parse_gtfs_time(row.get("departure_time", "")))
            )

        best: Dict[Tuple[str, str], Tuple[int, str, Optional[str]]] = {}
        departures: Dict[Tuple[str, str], Set[int]] = defaultdict(set)

        for trip_id, stops in trips.items():
            stops.sort(key=lambda x: x[0])
            train_type, line = trip_info.get(trip_id, ("Media Distancia", None))
            for i, (_, from_id, _, dep) in enumerate(stops):
                if dep is None:
                    continue
                for _, to_id, arr, _ in stops[i + 1:]:
                    if arr is None or to_id == from_id or arr <= dep:
                        continue
                    key = (from_id, to_id)
                    minutes = round((arr - dep) / 60)
                    if key not in best or minutes < best[key][0]:
                        best[key] = (minutes, train_type, line)
                    # Same clock time on different service days counts once
                    departures[key].add(dep % 86400)

        return [
            Segment(
                from_station_id=from_id,
                to_station_id=to_id,
                duration_minutes=minutes,
                train_type=train_type,
                frequency_daily=max(1, len(departures[(from_id, to_id)])),
                line=line,
            )
            for (from_id, to_id), (minutes, train_type, line) in best.items()
        ]

    def get_all_stations(self) -> List[Station]:
        if self._loaded_gtfs:
            return list(self._stations.values())
        return self.fallback_provider.get_all_stations()

    def get_all_segments(self) -> List[Segment]:
        if self._loaded_gtfs:
            return list(self._segments)
        return self.fallback_provider.get_all_segments()
