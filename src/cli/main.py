import sys
from pathlib import Path

# Ensure project root is in sys.path when invoked directly as a script
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import date, timedelta
from typing import List, Optional, Tuple
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich import box

from src.core.models import (
    Accommodation,
    AccommodationType,
    FilterParams,
    RouteOption,
    SortCriterion,
    Station,
)
from src.core.router import RailRouter, parse_travel_time_to_minutes
from src.core.sorter import filter_and_sort_accommodations
from src.providers.accommodation import get_accommodation_provider
from src.providers.rail import get_rail_provider

app = typer.Typer(
    name="escapadas",
    help="Descubre escapadas de fin de semana en tren de Media Distancia y aloja a tu medida."
)
console = Console()


def parse_stay_dates(checkin: Optional[str], checkout: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    """
    Parses ISO check-in/check-out dates. Returns (None, None) with a warning when they are
    invalid, incomplete or inconsistent, so the search falls back to standard nightly rates.
    """
    if not checkin and not checkout:
        return None, None
    if not (checkin and checkout):
        console.print("[yellow]Advertencia: indica tanto la fecha de entrada como la de salida. Se utilizarán tarifas estándar.[/yellow]")
        return None, None
    try:
        ci_date = date.fromisoformat(checkin)
        co_date = date.fromisoformat(checkout)
    except ValueError:
        console.print("[yellow]Advertencia: formato de fecha inválido (usar AAAA-MM-DD). Se utilizarán tarifas estándar.[/yellow]")
        return None, None
    if co_date <= ci_date:
        console.print("[yellow]Advertencia: la fecha de salida debe ser posterior a la de entrada. Se utilizarán tarifas estándar.[/yellow]")
        return None, None
    if ci_date < date.today():
        console.print("[yellow]Advertencia: la fecha de entrada ya ha pasado. Se utilizarán tarifas estándar.[/yellow]")
        return None, None
    return ci_date, co_date


def next_weekend_dates() -> Tuple[date, date]:
    """Returns the next Friday (today if it is Friday) and the following Sunday."""
    today = date.today()
    friday = today + timedelta(days=(4 - today.weekday()) % 7)
    return friday, friday + timedelta(days=2)


def display_welcome_banner():
    banner = """[bold cyan]╔══════════════════════════════════════════════════════════════╗
║        🚄 ESCAPADAS EN TREN (MEDIA DISTANCIA) & ALOJAMIENTOS 🏨        ║
╚══════════════════════════════════════════════════════════════╝[/bold cyan]
[dim]Descubre destinos alcanzables por tiempo de viaje y encuentra los mejores alojamientos.[/dim]"""
    console.print(Panel(banner, border_style="cyan"))


def display_stations_list(stations: List[Station]):
    table = Table(title="🚉 Estaciones Disponibles en la Red", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Código", style="dim", width=8)
    table.add_column("Estación", style="bold")
    table.add_column("Ciudad / Provincia")
    table.add_column("Comunidad Autónoma", style="cyan")

    for s in sorted(stations, key=lambda x: (x.autonomous_community, x.name)):
        table.add_row(s.id, s.name, f"{s.city} ({s.province})", s.autonomous_community)

    console.print(table)


def display_destinations_table(origin: Station, routes: List[RouteOption], max_minutes: int):
    table = Table(
        title=f"🎯 Destinos Alcanzables desde [bold green]{origin.name}[/bold green] (Máx. {max_minutes // 60}h {max_minutes % 60:02d}m)",
        box=box.HEAVY_EDGE,
        header_style="bold magenta",
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Destino", style="bold white", min_width=20)
    table.add_column("Tiempo Trayecto", justify="center", style="bold yellow")
    table.add_column("Tipo de Ruta", justify="center")
    table.add_column("Tren / Línea", style="cyan")
    table.add_column("Frecuencia Diaria", justify="center", style="green")

    for i, r in enumerate(routes, 1):
        route_type = "[green]Directo[/green]" if r.is_direct else f"[yellow]1 Transbordo ({r.transfer_station.name})[/yellow]"
        table.add_row(
            str(i),
            r.destination.name,
            r.duration_formatted,
            route_type,
            r.train_types_formatted,
            f"~{r.estimated_frequency_daily} trenes/día",
        )

    console.print(table)


def display_accommodations_table(destination_name: str, accommodations: List[Accommodation], sort_criterion: SortCriterion):
    if not accommodations:
        console.print(f"\n[yellow]⚠️ No se encontraron alojamientos disponibles en {destination_name} con los filtros aplicados.[/yellow]")
        return

    has_dates = bool(accommodations and accommodations[0].checkin_date and accommodations[0].checkout_date)
    date_title = f" (Fechas: [yellow]{accommodations[0].checkin_date.strftime('%d/%m')}[/yellow] a [yellow]{accommodations[0].checkout_date.strftime('%d/%m')}[/yellow])" if has_dates else ""

    table = Table(
        title=f"🏨 Alojamientos en [bold green]{destination_name}[/bold green]{date_title} (Orden: [cyan]{sort_criterion.value}[/cyan])",
        box=box.ROUNDED,
        header_style="bold blue",
    )
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Nombre del Alojamiento", style="bold white", min_width=24)
    table.add_column("Tipo", justify="center")
    table.add_column("Precio/Noche", justify="right", style="bold green")
    if has_dates and accommodations[0].nights_count > 1:
        table.add_column("Total Estancia", justify="right", style="bold cyan")
    table.add_column("Nota", justify="center", style="bold yellow")
    table.add_column("Reseñas", justify="right", style="dim")
    table.add_column("Calidad/Precio", justify="center", style="magenta")
    table.add_column("Enlace de Reserva", style="underline blue")

    for i, acc in enumerate(accommodations, 1):
        type_badge = "[blue]Hotel[/blue]" if acc.type == AccommodationType.HOTEL else "[cyan]Apartamento[/cyan]"
        rating_color = "green" if acc.rating >= 9.0 else ("yellow" if acc.rating >= 8.0 else "white")
        rating_str = f"[{rating_color}]{acc.rating_formatted}[/{rating_color}]"

        row = [
            str(i),
            escape(acc.name),
            type_badge,
            acc.price_formatted,
        ]
        if has_dates and accommodations[0].nights_count > 1:
            row.append(acc.total_price_formatted)
        row.extend([
            rating_str,
            f"{acc.reviews_count:,} ops",
            f"{acc.value_score}/10",
            escape(acc.booking_url),
        ])
        table.add_row(*row)

    console.print(table)


@app.command(name="interactive", help="Modo interactivo paso a paso.")
def interactive_wizard():
    """Ejecuta el asistente guiado para buscar escapadas y alojamientos."""
    display_welcome_banner()

    rail_provider = get_rail_provider()
    router = RailRouter(rail_provider=rail_provider)
    acc_provider = get_accommodation_provider()

    # 1. Origen
    while True:
        origin_input = Prompt.ask("\n[bold]1. Introduce la estación o población de origen[/bold] (ej. Santiago de Compostela, Madrid-Atocha)")
        origin_station = router.find_station(origin_input)
        if origin_station:
            console.print(f"   [green]✓ Estación identificada:[/green] [bold]{origin_station.name}[/bold] ({origin_station.province}, {origin_station.autonomous_community})")
            break
        else:
            console.print(f"   [red]✗ No se encontró ninguna estación con '{escape(origin_input)}'.[/red]")
            if Confirm.ask("   ¿Deseas ver la lista de estaciones disponibles?"):
                display_stations_list(rail_provider.get_all_stations())

    # 2. Límite de tiempo
    time_input = Prompt.ask(
        "\n[bold]2. Límite máximo de tiempo de viaje[/bold] (ej. 'hasta 2 horas y 30 minutos', '2h', '150')",
        default="hasta 2 horas y 30 minutos"
    )
    max_minutes = parse_travel_time_to_minutes(time_input)
    console.print(f"   [green]✓ Umbral de tiempo fijado en:[/green] [bold]{max_minutes // 60}h {max_minutes % 60:02d}m[/bold] ({max_minutes} minutos)")

    # 3. Tipo de alojamiento
    console.print("\n[bold]3. Selecciona el tipo de alojamiento a buscar:[/bold]")
    console.print("   [1] Hoteles\n   [2] Apartamentos\n   [3] Ambos")
    acc_type_choice = Prompt.ask("   Elige una opción", choices=["1", "2", "3"], default="3")
    type_map = {"1": AccommodationType.HOTEL, "2": AccommodationType.APARTMENT, "3": AccommodationType.BOTH}
    selected_acc_type = type_map[acc_type_choice]

    # 4. Criterio de ordenación
    console.print("\n[bold]4. Selecciona el criterio de ordenación para los alojamientos:[/bold]")
    console.print("   [1] Relación calidad/precio (Recomendado)\n   [2] Mejor nota\n   [3] Precio más bajo\n   [4] Precio más alto")
    sort_choice = Prompt.ask("   Elige una opción", choices=["1", "2", "3", "4"], default="1")
    sort_map = {
        "1": SortCriterion.VALUE_FOR_MONEY,
        "2": SortCriterion.BEST_RATING,
        "3": SortCriterion.PRICE_LOWEST,
        "4": SortCriterion.PRICE_HIGHEST,
    }
    selected_sort = sort_map[sort_choice]

    # Opciones de presupuesto adicionales (opcional)
    apply_budget = Confirm.ask("\n¿Deseas fijar un rango de presupuesto por noche?", default=False)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    if apply_budget:
        min_price = FloatPrompt.ask("   Precio mínimo (€ por noche, 0 para omitir)", default=0.0)
        max_price = FloatPrompt.ask("   Precio máximo (€ por noche, 0 para omitir)", default=0.0)
        min_price = min_price if min_price > 0 else None
        max_price = max_price if max_price > 0 else None

    # Cálculo de rutas ferroviarias
    with console.status("[bold green]Trazando rutas directas y con enlace simple en Media Distancia...[/bold green]"):
        routes = router.find_reachable_destinations(origin=origin_station, max_duration_minutes=max_minutes)

    if not routes:
        console.print(f"\n[red]No se encontraron destinos de Media Distancia alcanzables desde {origin_station.name} en {max_minutes} minutos o menos.[/red]")
        console.print("[dim]Prueba a aumentar el tiempo de viaje máximo.[/dim]")
        return

    console.print(f"\n[bold green]✓ Se encontraron {len(routes)} destinos alcanzables.[/bold green]\n")
    display_destinations_table(origin=origin_station, routes=routes, max_minutes=max_minutes)

    # Selección de destino para explorar alojamientos
    console.print("\n[bold]Elige qué deseas hacer:[/bold]")
    console.print("   [0] Ver alojamientos para TODOS los destinos encontrados")
    for idx, r in enumerate(routes, 1):
        console.print(f"   [{idx}] Ver alojamientos en {r.destination.name} ({r.duration_formatted})")

    while True:
        dest_choice = IntPrompt.ask("Introduce el número de opción", default=1)
        if 0 <= dest_choice <= len(routes):
            break
        console.print(f"   [red]Opción no válida. Elige un número entre 0 y {len(routes)}.[/red]")

    # 5. Fechas de estancia (cálculo de precios exactos)
    sel_checkin: Optional[date] = None
    sel_checkout: Optional[date] = None
    ask_dates = Confirm.ask("\n📅 ¿Deseas seleccionar fechas exactas de estancia para consultar precios reales?", default=True)
    if ask_dates:
        def_cin, def_cout = next_weekend_dates()
        cin_input = Prompt.ask("   Fecha de entrada (Check-in, AAAA-MM-DD)", default=def_cin.isoformat())
        cout_input = Prompt.ask("   Fecha de salida (Check-out, AAAA-MM-DD)", default=def_cout.isoformat())
        sel_checkin, sel_checkout = parse_stay_dates(cin_input, cout_input)
        if sel_checkin and sel_checkout:
            nights = (sel_checkout - sel_checkin).days
            console.print(f"   [green]✓ Estancia fijada:[/green] [bold]{nights} noche{'s' if nights > 1 else ''}[/bold] ({sel_checkin.strftime('%d/%m/%Y')} al {sel_checkout.strftime('%d/%m/%Y')})")

    filter_params = FilterParams(
        accommodation_type=selected_acc_type,
        sort_by=selected_sort,
        min_price=min_price,
        max_price=max_price,
        checkin_date=sel_checkin,
        checkout_date=sel_checkout,
    )

    if dest_choice == 0:
        # Ver para todos los destinos
        for r in routes:
            with console.status(f"[bold cyan]Buscando alojamientos en {r.destination.name}...[/bold cyan]"):
                raw_accs = acc_provider.search(
                    destination_name=r.destination.city or r.destination.name,
                    acc_type=selected_acc_type,
                    max_price=max_price,
                    checkin_date=sel_checkin,
                    checkout_date=sel_checkout,
                )
                filtered_accs = filter_and_sort_accommodations(raw_accs, filter_params)
            display_accommodations_table(r.destination.name, filtered_accs, selected_sort)
    else:
        selected_route = routes[dest_choice - 1]
        with console.status(f"[bold cyan]Consultando disponibilidad de alojamientos en {selected_route.destination.name}...[/bold cyan]"):
            raw_accs = acc_provider.search(
                destination_name=selected_route.destination.city or selected_route.destination.name,
                acc_type=selected_acc_type,
                max_price=max_price,
                checkin_date=sel_checkin,
                checkout_date=sel_checkout,
            )
            filtered_accs = filter_and_sort_accommodations(raw_accs, filter_params)
        display_accommodations_table(selected_route.destination.name, filtered_accs, selected_sort)


@app.command(name="search", help="Búsqueda directa por parámetros de línea de comandos.")
def search_command(
    origin: str = typer.Option(..., "--origin", "-o", help="Estación o población de origen (ej. 'Santiago de Compostela')"),
    max_time: str = typer.Option("2h 30m", "--max-time", "-t", help="Tiempo máximo de viaje (ej. '2h 30m', '150')"),
    acc_type: str = typer.Option("Ambos", "--acc-type", "-a", help="Tipo de alojamiento: 'Hoteles', 'Apartamentos' o 'Ambos'"),
    sort: str = typer.Option("Relación calidad/precio", "--sort", "-s", help="Criterio: 'Mejor nota', 'Precio más bajo', 'Precio más alto', 'Relación calidad/precio'"),
    destination: Optional[str] = typer.Option(None, "--dest", "-d", help="Destino específico (opcional, si se omite muestra los 3 más cercanos)"),
    max_price: Optional[float] = typer.Option(None, "--max-price", "-p", help="Precio máximo por noche en €"),
    checkin: Optional[str] = typer.Option(None, "--checkin", "-ci", help="Fecha de entrada (Check-in, formato AAAA-MM-DD)"),
    checkout: Optional[str] = typer.Option(None, "--checkout", "-co", help="Fecha de salida (Check-out, formato AAAA-MM-DD)"),
):
    """Ejecuta una búsqueda directa sin asistente interactivo."""
    rail_provider = get_rail_provider()
    router = RailRouter(rail_provider=rail_provider)
    acc_provider = get_accommodation_provider()

    origin_station = router.find_station(origin)
    if not origin_station:
        console.print(f"[red]Error: Estación de origen '{escape(origin)}' no encontrada en la red.[/red]")
        raise typer.Exit(code=1)

    max_minutes = parse_travel_time_to_minutes(max_time)
    routes = router.find_reachable_destinations(origin=origin_station, max_duration_minutes=max_minutes)

    if not routes:
        console.print(f"[yellow]No se encontraron destinos alcanzables desde {origin_station.name} en {escape(max_time)}.[/yellow]")
        raise typer.Exit(code=0)

    display_destinations_table(origin_station, routes, max_minutes)

    target_routes = routes[:3]  # Without --dest, show accommodations for the closest destinations
    if destination:
        dest_station = router.find_station(destination)
        if not dest_station:
            console.print(f"[red]Error: Destino '{escape(destination)}' no encontrado en la red.[/red]")
            raise typer.Exit(code=1)
        target_routes = [r for r in routes if r.destination.id == dest_station.id]
        if not target_routes:
            console.print(f"[yellow]{dest_station.name} no es alcanzable desde {origin_station.name} en {max_minutes} minutos o menos.[/yellow]")
            raise typer.Exit(code=0)

    ci_date, co_date = parse_stay_dates(checkin, checkout)

    filters = FilterParams(
        accommodation_type=AccommodationType.from_str(acc_type),
        sort_by=SortCriterion.from_str(sort),
        max_price=max_price,
        checkin_date=ci_date,
        checkout_date=co_date,
    )

    for r in target_routes:
        accs = acc_provider.search(
            r.destination.city or r.destination.name,
            acc_type=filters.accommodation_type,
            max_price=max_price,
            checkin_date=ci_date,
            checkout_date=co_date,
        )
        filtered = filter_and_sort_accommodations(accs, filters)
        display_accommodations_table(r.destination.name, filtered, filters.sort_by)


@app.command(name="stations", help="Lista todas las estaciones de Media Distancia disponibles.")
def list_stations():
    rail_provider = get_rail_provider()
    display_stations_list(rail_provider.get_all_stations())


if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_wizard()
    else:
        app()
