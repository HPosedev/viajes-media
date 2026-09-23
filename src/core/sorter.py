import math
from typing import List
from src.core.models import (
    Accommodation,
    AccommodationType,
    FilterParams,
    RouteOption,
    SortCriterion,
)


def calculate_value_score(
    item: Accommodation,
    min_price_sample: float,
    max_price_sample: float
) -> float:
    """
    Computes a balanced Quality/Price index (0.0 to 10.0 scale).
    - Higher rating -> higher score
    - Lower price -> higher score
    - Higher review count -> higher statistical confidence (dampens inflated 10.0 with 1 review)
    """
    rating_ratio = max(0.0, min(10.0, item.rating)) / 10.0

    # Price factor (cheaper gets up to 1.0, most expensive ~ 0.4)
    price_span = max(max_price_sample - min_price_sample, 1.0)
    relative_price = (item.price_per_night - min_price_sample) / price_span
    price_factor = max(0.35, 1.0 - (relative_price * 0.55))

    # Social proof confidence factor (log scale based on reviews up to 500)
    review_weight = min(1.0, math.log10(max(1, item.reviews_count) + 1) / math.log10(501))
    confidence_factor = 0.75 + (0.25 * review_weight)

    score = rating_ratio * price_factor * confidence_factor * 10.0
    return round(score, 2)


def filter_and_sort_accommodations(
    accommodations: List[Accommodation],
    filters: FilterParams
) -> List[Accommodation]:
    """Applies type, price, and rating filters, updates value scores, and sorts according to criterion."""
    if not accommodations:
        return []

    # 1. Filter by Accommodation Type
    filtered = []
    for item in accommodations:
        if filters.accommodation_type != AccommodationType.BOTH:
            if item.type != filters.accommodation_type:
                continue

        # Filter by Price Range
        if filters.min_price is not None and item.price_per_night < filters.min_price:
            continue
        if filters.max_price is not None and item.price_per_night > filters.max_price:
            continue

        # Filter by Minimum Rating
        if filters.min_rating is not None and item.rating < filters.min_rating:
            continue

        filtered.append(item)

    if not filtered:
        return []

    # 2. Calculate value score dynamically based on active filtered sample
    prices = [acc.price_per_night for acc in filtered]
    min_p, max_p = min(prices), max(prices)
    for acc in filtered:
        acc.value_score = calculate_value_score(acc, min_p, max_p)

    # 3. Sort according to specified criterion
    if filters.sort_by == SortCriterion.BEST_RATING:
        filtered.sort(key=lambda x: (-x.rating, -x.reviews_count, x.price_per_night))
    elif filters.sort_by == SortCriterion.PRICE_LOWEST:
        filtered.sort(key=lambda x: (x.price_per_night, -x.rating))
    elif filters.sort_by == SortCriterion.PRICE_HIGHEST:
        filtered.sort(key=lambda x: (-x.price_per_night, -x.rating))
    elif filters.sort_by == SortCriterion.VALUE_FOR_MONEY:
        filtered.sort(key=lambda x: (-x.value_score, -x.rating, x.price_per_night))

    return filtered


def sort_routes(routes: List[RouteOption], sort_by_duration: bool = True) -> List[RouteOption]:
    """Sorts route options by duration or frequency."""
    if sort_by_duration:
        return sorted(routes, key=lambda r: (r.total_duration_minutes, not r.is_direct, -r.estimated_frequency_daily))
    return sorted(routes, key=lambda r: (-r.estimated_frequency_daily, r.total_duration_minutes))
