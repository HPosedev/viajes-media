import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from src.config import settings
from src.core.models import Segment, Station
from src.providers.base import RailDataProvider

logger = logging.getLogger(__name__)


class LocalGraphRailProvider(RailDataProvider):
    """
    Rail data provider loading curated Media Distancia networks from JSON.
    Acts as the primary fast offline provider and fallback.
    """

    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or settings.SEED_ROUTES_PATH
        self._stations_by_id: Dict[str, Station] = {}
        self._segments: List[Segment] = []
        self._load_data()

    def _load_data(self) -> None:
        if not self.data_file.exists():
            logger.warning("Seed routes file not found at %s. Using empty network.", self.data_file)
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for s_dict in data.get("stations", []):
                station = Station.model_validate(s_dict)
                self._stations_by_id[station.id] = station

            for r_dict in data.get("routes", []):
                segment = Segment(
                    from_station_id=r_dict["from"],
                    to_station_id=r_dict["to"],
                    duration_minutes=r_dict["duration_minutes"],
                    train_type=r_dict.get("train_type", "Media Distancia"),
                    frequency_daily=r_dict.get("frequency_daily", 6),
                    line=r_dict.get("line"),
                )
                self._segments.append(segment)

        except Exception as e:
            logger.error("Error reading rail seed data: %s", e)

    def get_all_stations(self) -> List[Station]:
        return list(self._stations_by_id.values())

    def get_all_segments(self) -> List[Segment]:
        return list(self._segments)
