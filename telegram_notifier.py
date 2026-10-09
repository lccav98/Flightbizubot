"""
Notificador e Bot Interativo do Telegram para envio de alertas 24/7 e resposta a comandos.
"""
from __future__ import annotations

import html
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from rich.console import Console

from config import settings
from flight_engine import FlightOffer
from car_engine import CarRentalDeal
from promo_engine import PromoItem
import database

console = Console()

class TelegramNotifier:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.default_chat_id = str(settings.TELEGRAM_CHAT_ID) if settings.TELEGRAM_CHAT_ID else ""
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)

    def send_to_chat(self, chat_id: str, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = False) -> bool:
        """Envia mensagem para um chat_id específico."""
        if not self.is_configured or not chat_id:
            console.log(f"[yellow][TELEGRAM NÃO CONFIGURADO][/yellow] Mensagem simulada para {chat_id}:\n{text[:200]}...")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return True
                elif res.status_code in (403, 400):
                    # Usuário bloqueou o bot ou chat inválido
                    console.log(f"[yellow]Usuário {chat_id} desativado (status {res.status_code}).[/yellow]")
                    database.set_subscriber_status(chat_id, False)
                    return False
                else:
                    console.log(f"[red]Erro Telegram ({chat_id}):[/red] {res.status_code} - {res.text}")
                    return False
        except Exception as e:
            console.log(f"[red]Exceção no envio para {chat_id}:[/red] {e}")
            return False

    def broadcast(self, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = False) -> int:
        """Transmite mensagem para todos os usuários inscritos no banco de dados."""
        if not self.is_configured:
            console.log(f"[yellow][BROADCAST SIMULADO][/yellow] {text[:200]}...")
            return 0

        subscribers = database.get_active_subscribers()
        if self.default_chat_id and self.default_chat_id not in subscribers:
            subscribers.append(self.default_chat_id)

        if not subscribers:
            console.log("[dim]Nenhum assinante ativo para broadcast.[/dim]")
            return 0

        success_count = 0
        for cid in set(subscribers):
            if self.send_to_chat(cid, text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview):
                success_count += 1
        return success_count

    def send_message(self, text: str, target_chat_id: Optional[str] = None, parse_mode: str = "HTML", disable_web_page_preview: bool = False) -> bool:
        """Envia mensagem para um chat específico ou realiza broadcast caso não seja informado."""
        if target_chat_id:
            return self.send_to_chat(target_chat_id, text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        return self.broadcast(text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview) > 0

    def notify_flight_deal(self, offer: FlightOffer, car_deal: Optional[CarRentalDeal] = None) -> bool:
        """Envia alerta de passagem aérea barata para todos os inscritos."""
        orig_dest = f"{offer.origin_name or offer.origin} ➔ {offer.dest_name or offer.destination}"
        
        stops_text = "Voo Direto" if offer.stops == 0 else f"{offer.stops} parada(s)"
        discount_text = f" (-{offer.discount_pct}% vs média)" if offer.discount_pct > 0 else ""
        
        trip_type_header = "🔄 <b>IDA E VOLTA</b>" if offer.is_round_trip else "➡️ <b>SOMENTE IDA</b>"
        if offer.is_round_trip and offer.return_date:
            dates_info = f"📅 <b>Ida:</b> {offer.flight_date} | <b>Volta:</b> {offer.return_date}"
        else:
            dates_info = f"📅 <b>Data:</b> {offer.flight_date}"

        links_bar = [f"<a href='{offer.deep_link}'>👉 Emitir no Google Flights</a>"]
        if getattr(offer, "kayak_link", None):
            links_bar.append(f"<a href='{offer.kayak_link}'>Kayak</a>")
        if getattr(offer, "airline_link", None):
            links_bar.append(f"<a href='{offer.airline_link}'>Site {offer.airline}</a>")

        msg = (
            f"🚨 <b>OFERTA DE VOO DETECTADA!</b> ({trip_type_header})\n\n"
            f"📍 <b>Trecho:</b> {orig_dest}\n"
            f"✈️ <b>Companhia:</b> {offer.airline} ({stops_text})\n"
            f"{dates_info}\n"
            f"💰 <b>Tarifa Total:</b> <code>R$ {offer.price:,.2f}</code>{discount_text}\n\n"
            f"🔗 {' | '.join(links_bar)}\n"
        )

        if car_deal:
            book_url = getattr(car_deal, "booking_link", "") or car_deal.comparator_link
            msg += (
                f"\n🚗 <b>Aluguel de Carro em {car_deal.city_name}:</b>\n"
                f"• Período: {car_deal.pickup_date} a {car_deal.return_date} ({car_deal.days} dias)\n"
                f"• Diária est.: {car_deal.currency} {car_deal.estimated_daily_price:.2f} (Total: {car_deal.currency} {car_deal.estimated_total_price:.2f})\n"
                f"• <a href='{book_url}'>Reservar Carro</a> | "
                f"<a href='{car_deal.comparator_link}'>Kayak</a> | "
                f"<a href='{car_deal.rentcars_link}'>Rentcars</a>\n"
            )

        return self.broadcast(msg) > 0

    def notify_promo_news(self, promo: PromoItem) -> bool:
        """Envia alerta de promoção relâmpago para todos os inscritos."""
        msg = (
            f"🔥 <b>PROMOÇÃO / NOTÍCIA RELÂMPAGO!</b>\n"
            f"📢 <b>Fonte:</b> {promo.source}\n"
            f"🏷️ <b>Título:</b> {promo.title}\n\n"
            f"📝 {promo.snippet}\n\n"
            f"🔗 <a href='{promo.link}'>Acessar Promoção Completa</a>"
        )
        return self.broadcast(msg) > 0

    def send_summary_report(self, lowest_prices: List[Dict[str, Any]], car_deals: List[CarRentalDeal], target_chat_id: Optional[str] = None):
        """Envia relatório consolidado das menores tarifas registradas."""
        lines = ["📊 <b>RESUMO DO RADAR DE VIAGENS 24/7</b>\n", "✈️ <b>Menores Tarifas por Trecho (Ida e Volta):</b>"]
        for p in lowest_prices:
            route = f"{p['origin']} ➔ {p['destination']}"
            price_str = f"R$ {p['min_price']:,.2f}"
            date_str = p.get("flight_date", "N/D")
            ret_str = p.get("return_date")
            dates_display = f"{date_str} a {ret_str}" if ret_str else date_str
            airline = p.get("airline", "")
            flight_url = p.get("deep_link", "")
            lines.append(
                f"• <b>{route}:</b> <code>{price_str}</code>\n"
                f"  ({dates_display} - {airline}) - <a href='{flight_url}'>Emitir no Google Flights</a>"
            )

        lines.append("\n🚗 <b>Locação de Veículos nos Destinos:</b>")
        for c in car_deals[:6]:
            b_link = getattr(c, "booking_link", "") or c.comparator_link
            lines.append(
                f"• <b>{c.city_name}:</b> {c.currency} {c.estimated_daily_price:.2f}/dia - "
                f"<a href='{b_link}'>Reservar</a> | <a href='{c.comparator_link}'>Kayak</a>"
            )

        lines.append("\n💡 <i>O agente continua monitorando 24 horas por dia.</i>")
        full_msg = "\n".join(lines)
        return self.send_message(full_msg, target_chat_id=target_chat_id)

    async def poll_telegram_commands(self, on_command_callback):
        """Loop assíncrono para ouvir mensagens e responder comandos de qualquer usuário."""
        if not self.is_configured:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    url = f"{self.base_url}/getUpdates"
                    params = {"offset": self.last_update_id + 1, "timeout": 20}
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            message = update.get("message", {})
                            text = message.get("text", "").strip()
                            chat = message.get("chat", {})
                            chat_id = str(chat.get("id", ""))
                            user_info = message.get("from", {})
                            
                            if chat_id and (text or message):
                                # Registra usuário ativo
                                username = user_info.get("username", "")
                                first_name = user_info.get("first_name", "")
                                database.register_or_update_subscriber(chat_id, username, first_name)

                                console.log(f"[cyan]Mensagem de {first_name or username} ({chat_id}):[/cyan] {text}")
                                await on_command_callback(self, text, chat_id, user_info)
                except Exception as e:
                    await asyncio.sleep(5)
                await asyncio.sleep(1)

telegram_notifier = TelegramNotifier()
