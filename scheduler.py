"""
Orquestrador e Agendador do Ciclo de Varredura 24/7.
"""
from __future__ import annotations

import sys
import time
import asyncio
import datetime
from typing import List, Dict, Any

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

from config import DEFAULT_ROUTES, settings
import database
import flight_engine
import car_engine
import promo_engine
from telegram_notifier import telegram_notifier, TelegramNotifier

console = Console()

class TravelRadarAgent:
    def __init__(self):
        self.is_running = False
        self.total_scans = 0
        self.started_at = datetime.datetime.now()

    def run_promo_scan(self):
        """Varre os feeds de notícias e promoções relâmpago."""
        console.log("[cyan]Verificando feeds de promoções relâmpago...[/cyan]")
        new_promos = promo_engine.scan_promotions()
        for promo in new_promos:
            console.log(f"[bold green]Promoção Encontrada:[/bold green] {promo.title}")
            telegram_notifier.notify_promo_news(promo)

    def run_full_flight_scan(self):
        """Executa a varredura completa das 12 rotas com grade flexível de datas."""
        self.total_scans += 1
        console.rule(f"[bold blue]Ciclo #{self.total_scans} de Varredura - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}[/bold blue]")
        
        # 1. Verifica notícias e feirões
        self.run_promo_scan()
        
        # 2. Gera datas distribuídas nos próximos meses (flexibilidade 6 a 12 meses)
        sample_dates = flight_engine.generate_sample_dates(months_ahead=settings.MONTHS_AHEAD)
        console.log(f"Analisando [bold]{len(DEFAULT_ROUTES)}[/bold] rotas em [bold]{len(sample_dates)}[/bold] datas estratégicas...")

        for route in DEFAULT_ROUTES:
            console.log(f"[yellow]Varrendo rota:[/yellow] {route.origin_name} ({route.origin}) ➔ {route.dest_name} ({route.destination})")
            
            try:
                offers = flight_engine.scan_route_flexible(route, sample_dates)
                if not offers:
                    console.log(f"[dim]Nenhuma tarifa válida encontrada para {route.origin}->{route.destination}[/dim]")
                    continue

                # Pega a menor tarifa desta rota encontrada neste ciclo
                best_offer = min(offers, key=lambda x: x.price)
                console.log(f"-> Menor tarifa: [green]R$ {best_offer.price:,.2f}[/green] ({best_offer.flight_date} via {best_offer.airline})")

                # Verifica se deve disparar alerta no Telegram
                if database.should_send_flight_alert(
                    origin=best_offer.origin,
                    destination=best_offer.destination,
                    flight_date=best_offer.flight_date,
                    price=best_offer.price,
                    max_threshold=route.max_price_alert
                ):
                    console.log(f"[bold magenta]🔔 ALERTA DISPARADO PARA TELEGRAM:[/bold magenta] R$ {best_offer.price:,.2f}")
                    
                    # Cotação de veículo no destino alinhada com as datas da viagem
                    car_deal = car_engine.check_car_rentals_for_destination(
                        best_offer.destination,
                        pickup_date=best_offer.flight_date,
                        return_date=best_offer.return_date
                    )
                    
                    # Envia notificação rica no Telegram
                    sent = telegram_notifier.notify_flight_deal(best_offer, car_deal)
                    if sent:
                        database.mark_alert_sent(
                            alert_type="flight_deal",
                            lookup_key=f"flight:{best_offer.origin}:{best_offer.destination}:{best_offer.flight_date}",
                            price=best_offer.price
                        )
            except Exception as e:
                console.log(f"[red]Erro ao processar rota {route.origin}->{route.destination}:[/red] {e}")

        console.log(f"[green]Ciclo #{self.total_scans} concluído com sucesso![/green]")

    async def handle_telegram_command(self, notifier: TelegramNotifier, cmd: str, chat_id: str, user_info: dict = None):
        """Processa os comandos enviados por qualquer usuário no Telegram com respostas direcionadas."""
        user_info = user_info or {}
        first_name = user_info.get("first_name", "Viajante")
        username = user_info.get("username", "")

        # Registra / atualiza assinante
        database.register_or_update_subscriber(chat_id, username, first_name)

        tokens = cmd.strip().split()
        cmd_clean = tokens[0].lower() if tokens else ""
        arg = tokens[1].lower() if len(tokens) > 1 else ""

        if cmd_clean in ["/start", "/ajuda", "/help"]:
            help_msg = (
                f"👋 <b>Olá, {first_name}! Bem-vindo ao Flight Bizu Bot!</b> ✈️\n\n"
                "Sou o seu radar inteligente de viagens e locação de veículos 24/7.\n\n"
                "🔔 <b>Status dos seus Alertas:</b> <code>ATIVADOS</code> ✅\n"
                "Você receberá alertas automáticos sempre que encontrarmos voos com super desconto (Ida e Volta até 12 meses à frente) ou promoções relâmpago de passagens!\n\n"
                "📌 <b>Comandos disponíveis:</b>\n"
                "• /menores - Menores tarifas históricas registradas\n"
                "• /carros - Cotações e links de aluguel de carros nos destinos\n"
                "• /promos - Notícias e feirões de passagens recentes\n"
                "• /buscar - Força uma varredura de voos agora\n"
                "• /alertas - Ativar ou pausar alertas automáticos\n"
                "• /status - Status do agente em tempo real\n\n"
                "🔗 <b>Compartilhe com amigos:</b> https://t.me/Flightbizubot"
            )
            notifier.send_to_chat(chat_id, help_msg)

        elif cmd_clean == "/alertas":
            if arg in ["off", "desativar", "parar", "pause"]:
                database.set_subscriber_status(chat_id, False)
                notifier.send_to_chat(chat_id, "🔕 <b>Alertas automáticos desativados.</b> Você ainda pode usar /menores, /carros e /promos sempre que quiser! Digite <code>/alertas on</code> para reativar.")
            elif arg in ["on", "ativar", "ligar"]:
                database.set_subscriber_status(chat_id, True)
                notifier.send_to_chat(chat_id, "🔔 <b>Alertas automáticos ativados com sucesso!</b> Você será avisado 24/7 sempre que surgir uma super oportunidade.")
            else:
                is_active = database.is_subscriber_active(chat_id)
                status_txt = "ATIVADOS 🔔" if is_active else "DESATIVADOS 🔕"
                msg = (
                    f"⚙️ <b>Configuração de Alertas:</b> {status_txt}\n\n"
                    "Para alterar, use:\n"
                    "• <code>/alertas on</code> - Ativar alertas automáticos\n"
                    "• <code>/alertas off</code> - Pausar alertas automáticos"
                )
                notifier.send_to_chat(chat_id, msg)

        elif cmd_clean == "/menores":
            lowest = database.get_all_lowest_prices()
            if not lowest:
                notifier.send_to_chat(chat_id, "ℹ️ Ainda não há dados suficientes gravados. O agente está coletando tarifas!")
                return
            
            lines = ["✈️ <b>Menores Tarifas Registradas (Ida e Volta):</b>\n"]
            for item in lowest:
                ret_info = f" a {item['return_date']}" if item.get('return_date') else ""
                deep_link = item.get('deep_link') or ""
                if not deep_link or "travel/flights?q=" in deep_link:
                    deep_link = flight_engine.build_google_flights_url(
                        item['origin'], item['destination'], item['flight_date'], item.get('return_date')
                    )
                kayak_url = flight_engine.build_kayak_flights_url(
                    item['origin'], item['destination'], item['flight_date'], item.get('return_date')
                )
                lines.append(
                    f"• <b>{item['origin']} ➔ {item['destination']}:</b> <code>R$ {item['min_price']:,.2f}</code> "
                    f"({item['flight_date']}{ret_info} - {item['airline']})\n"
                    f"  <a href='{deep_link}'>👉 Emitir no Google Flights</a> | <a href='{kayak_url}'>Kayak</a>"
                )
            notifier.send_to_chat(chat_id, "\n".join(lines))

        elif cmd_clean == "/carros":
            deals = car_engine.check_all_car_destinations()
            lines = ["🚗 <b>Locação de Veículos nos Destinos Monitorados:</b>\n"]
            for d in deals:
                b_link = getattr(d, 'booking_link', '') or d.comparator_link
                lines.append(
                    f"• <b>{d.city_name} ({d.destination_code}):</b> "
                    f"Diária a partir de <b>{d.currency} {d.estimated_daily_price:.2f}</b>\n"
                    f"  🔗 <a href='{b_link}'>Reservar Veículo</a> | "
                    f"<a href='{d.comparator_link}'>Kayak</a> | "
                    f"<a href='{d.rentcars_link}'>Rentcars</a>\n"
                )
            notifier.send_to_chat(chat_id, "\n".join(lines))

        elif cmd_clean == "/promos":
            recent = database.get_recent_promotions(limit=5)
            if not recent:
                notifier.send_to_chat(chat_id, "ℹ️ Nenhuma promoção relâmpago nova detectada recentemente.")
                return
            lines = ["🔥 <b>Promoções e Feirões Recentes:</b>\n"]
            for p in recent:
                lines.append(f"• <b>{p['source']}:</b> {p['title']}\n  <a href='{p['link']}'>Ver detalhes</a>\n")
            notifier.send_to_chat(chat_id, "\n".join(lines))

        elif cmd_clean == "/buscar":
            notifier.send_to_chat(chat_id, "⏳ <b>Iniciando varredura manual de todos os trechos...</b>\nVocê receberá o relatório completo em instantes.")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.run_full_flight_scan)
            lowest = database.get_all_lowest_prices()
            car_deals = car_engine.check_all_car_destinations()
            notifier.send_summary_report(lowest, car_deals, target_chat_id=chat_id)

        elif cmd_clean == "/status":
            uptime = datetime.datetime.now() - self.started_at
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            total_users = database.count_active_subscribers()
            status_msg = (
                "🟢 <b>Status do Flight Bizu Bot 24/7:</b> ONLINE\n\n"
                f"⏱️ <b>Tempo Ativo:</b> {hours}h {minutes}m\n"
                f"🔄 <b>Ciclos de Varredura Executados:</b> {self.total_scans}\n"
                f"⏰ <b>Intervalo entre Ciclos:</b> {settings.SCAN_INTERVAL_MINUTES} minutos\n"
                f"👥 <b>Viajantes Inscritos:</b> {total_users}\n"
                f"✈️ <b>Rotas Monitoradas:</b> {len(DEFAULT_ROUTES)} trechos (Ida e Volta)\n"
                f"📁 <b>Banco de Dados:</b> Operacional\n"
            )
            notifier.send_to_chat(chat_id, status_msg)
        else:
            # Mensagem desconhecida ou texto livre
            fallback_msg = (
                f"Olá, {first_name}! 😊\n"
                "Para consultar voos e carros, use um dos comandos:\n\n"
                "• /menores - Ver as menores tarifas aéreas\n"
                "• /carros - Ver aluguel de veículos\n"
                "• /promos - Ver promoções e feirões\n"
                "• /buscar - Fazer uma nova busca agora\n"
                "• /status - Ver status do robô\n"
                "• /ajuda - Exibir instruções completas"
            )
            notifier.send_to_chat(chat_id, fallback_msg)

    async def start_24_7_loop(self):
        """Inicia os loops assíncronos de varredura periódica e escuta de comandos Telegram."""
        self.is_running = True
        database.init_db()
        console.log("[bold green]Iniciando Radar de Viagens & Veículos 24/7![/bold green]")

        # Tarefa 1: Ouvir comandos do Telegram
        command_task = asyncio.create_task(
            telegram_notifier.poll_telegram_commands(self.handle_telegram_command)
        )

        # Tarefa 2: Loop de varredura a cada intervalo configurado
        while self.is_running:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.run_full_flight_scan)
            except Exception as e:
                console.log(f"[red]Erro inesperado no ciclo de varredura:[/red] {e}")

            console.log(f"Dormindo por [bold]{settings.SCAN_INTERVAL_MINUTES}[/bold] minutos até o próximo ciclo...")
            await asyncio.sleep(settings.SCAN_INTERVAL_MINUTES * 60)

        await command_task

agent = TravelRadarAgent()
