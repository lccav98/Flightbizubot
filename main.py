"""
Ponto de entrada principal do Agente Radar de Viagens & Veículos 24/7.
"""
from __future__ import annotations

import sys
import argparse
import asyncio

# Garante suporte UTF-8 e redirecionamento de log quando executado sem console (background)
if sys.stdout is None:
    sys.stdout = open("radar.log", "a", encoding="utf-8", buffering=1)
elif hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr is None:
    sys.stderr = open("radar_err.log", "a", encoding="utf-8", buffering=1)
elif hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from rich.console import Console
from rich.table import Table


import database
from config import settings, DEFAULT_ROUTES, CAR_RENTAL_DESTINATIONS
import car_engine
import promo_engine
from scheduler import agent

console = Console()

def show_car_table():
    """Exibe no terminal a tabela com os 12 destinos de locação de veículos."""
    deals = car_engine.check_all_car_destinations()
    table = Table(title="🚗 Locação de Veículos nos Destinos Monitorados", show_lines=True)
    table.add_column("Destino", style="bold cyan")
    table.add_column("País", style="white")
    table.add_column("Diária Est.", style="green")
    table.add_column("Total 5d", style="bold green")
    table.add_column("Locadoras Recomendadas", style="yellow")
    table.add_column("Link Reserva Direta", style="blue")
    table.add_column("Comparador Kayak", style="magenta")

    for d in deals:
        table.add_row(
            f"{d.city_name} ({d.destination_code})",
            d.country,
            f"{d.currency} {d.estimated_daily_price:.2f}",
            f"{d.currency} {d.estimated_total_price:.2f}",
            d.provider_recommendation,
            d.booking_link or d.rentcars_link,
            d.comparator_link
        )
    console.print(table)

def show_lowest_prices_table():
    """Exibe no terminal as menores tarifas registradas."""
    records = database.get_all_lowest_prices()
    if not records:
        console.print("[yellow]Nenhuma tarifa registrada ainda no banco de dados. Execute uma busca primeiro![/yellow]")
        return

    table = Table(title="✈️ Menores Tarifas Registradas no Histórico (Ida e Volta)", show_lines=True)
    table.add_column("Trecho", style="bold cyan")
    table.add_column("Tarifa Total", style="bold green")
    table.add_column("Período (Ida ➔ Volta)", style="yellow")
    table.add_column("Cia Aérea", style="white")
    table.add_column("Última Atualização", style="dim")

    for r in records:
        ret_date = r.get("return_date")
        dates_label = f"{r['flight_date']} ➔ {ret_date}" if ret_date else r["flight_date"]
        table.add_row(
            f"{r['origin']} ➔ {r['destination']}",
            f"R$ {r['min_price']:,.2f}",
            dates_label,
            r["airline"] or "N/D",
            str(r["recorded_at"])
        )
    console.print(table)

def show_promos_table():
    """Exibe as promoções recentes no terminal."""
    promos = promo_engine.scan_promotions()
    table = Table(title="🔥 Promoções e Feirões Detectados", show_lines=True)
    table.add_column("Fonte", style="bold cyan")
    table.add_column("Título", style="white")
    table.add_column("Palavra-Chave", style="yellow")
    table.add_column("Link", style="blue")

    for p in promos:
        table.add_row(p.source, p.title, p.relevant_keyword, p.link)
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Radar de Viagens & Veículos 24/7")
    parser.add_argument("--daemon", action="store_true", help="Inicia o agente no modo 24/7 contínuo")
    parser.add_argument("--run-once", action="store_true", help="Executa um único ciclo de varredura e finaliza")
    parser.add_argument("--cars", action="store_true", help="Mostra cotações e links de aluguel de veículos")
    parser.add_argument("--promos", action="store_true", help="Mostra promoções e feirões capturados")
    parser.add_argument("--status", action="store_true", help="Exibe menores tarifas salvas no banco")

    args = parser.parse_args()
    database.init_db()

    if args.cars:
        show_car_table()
    elif args.promos:
        show_promos_table()
    elif args.status:
        show_lowest_prices_table()
    elif args.run_once:
        console.print("[bold yellow]Executando ciclo único de teste...[/bold yellow]")
        agent.run_full_flight_scan()
        show_lowest_prices_table()
    else:
        # Modo padrão: iniciar 24/7
        console.print("[bold green]=================================================[/bold green]")
        console.print("[bold cyan]✈️  AGENTE RADAR DE VIAGENS & VEÍCULOS 24/7[/bold cyan]")
        console.print("[bold green]=================================================[/bold green]")
        console.print(f"• Trechos monitorados: [bold]{len(DEFAULT_ROUTES)}[/bold]")
        console.print(f"• Destinos para aluguel de carros: [bold]{len(CAR_RENTAL_DESTINATIONS)}[/bold]")
        console.print(f"• Intervalo de varredura: [bold]{settings.SCAN_INTERVAL_MINUTES} minutos[/bold]")
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            console.print("• Notificações Telegram: [bold green]ATIVAS[/bold green]")
        else:
            console.print("• Notificações Telegram: [bold yellow]PENDENTE CONFIGURAÇÃO (Veja o arquivo .env)[/bold yellow]")
        console.print("-------------------------------------------------")
        
        asyncio.run(agent.start_24_7_loop())

if __name__ == "__main__":
    main()
