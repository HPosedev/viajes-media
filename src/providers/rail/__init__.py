from pathlib import Path
from typing import Optional
from src.config import settings
from src.providers.base import RailDataProvider
from src.providers.rail.local_graph import LocalGraphRailProvider
from src.providers.rail.gtfs_provider import GTFSRailProvider


def get_rail_provider(gtfs_path: Optional[Path] = None) -> RailDataProvider:
    """Returns GTFSRailProvider if a GTFS feed is supplied (or set in GTFS_PATH), otherwise LocalGraphRailProvider."""
    gtfs_path = gtfs_path or settings.GTFS_PATH
    if gtfs_path and gtfs_path.exists():
        return GTFSRailProvider(gtfs_path=gtfs_path)
    return LocalGraphRailProvider()
