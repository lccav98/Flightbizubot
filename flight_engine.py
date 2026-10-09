"""
Mecanismo de busca e varredura de voos com Google Flights e suporte a Ida e Volta.
"""
from __future__ import annotations

import time
import random
import datetime
from dataclasses import dataclass
from typing import List, Optional

import httpx
from fast_flights.integrations.base import FetchIntegration
from fast_flights import create_query, FlightQuery, get_flights

from config import RouteConfig, DEFAULT_ROUTES, settings
import database

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

class ResilientHttpxFetch(FetchIntegration):
    """Fetcher customizado com rotação de headers e timeouts seguros."""
    def fetch_html(self, q) -> str:
        params = q.params() if hasattr(q, "params") else {"q": q}
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        }
        with httpx.Client(follow_redirects=True, timeout=25.0) as client:
            response = client.get("https://www.google.com/travel/flights", params=params, headers=headers)
            response.raise_for_status()
            return response.text

@dataclass
class FlightOffer:
    origin: str
    destination: str
    origin_name: str
    dest_name: str
    flight_date: str
    return_date: Optional[str]
    is_round_trip: bool
    price: float
    airline: str
    stops: int
    deep_link: str
    airline_link: str = ""
    kayak_link: str = ""
    is_deal: bool = False
    discount_pct: float = 0.0

fetcher_instance = ResilientHttpxFetch()

def build_google_flights_url(origin: str, dest: str, depart_date: str, return_date: Optional[str] = None) -> str:
    """
    Gera link direto e parametrizado com token TFS oficial do Google Flights
    para emissão imediata e seleção de bilhetes com rotas e datas pré-preenchidas.
    """
    try:
        if return_date:
            flight_queries = [
                FlightQuery(date=depart_date, from_airport=origin, to_airport=dest),
                FlightQuery(date=return_date, from_airport=dest, to_airport=origin)
            ]
            trip_type = "round-trip"
        else:
            flight_queries = [FlightQuery(date=depart_date, from_airport=origin, to_airport=dest)]
            trip_type = "one-way"

        q = create_query(
            flights=flight_queries,
            trip=trip_type,
            currency="BRL",
            language="pt-BR"
        )
        return q.url()
    except Exception:
        # Fallback estruturado
        if return_date:
            return f"https://www.google.com/travel/flights/search?hl=pt-BR&curr=BRL#flt={origin}.{dest}.{depart_date}*{dest}.{origin}.{return_date}"
        return f"https://www.google.com/travel/flights/search?hl=pt-BR&curr=BRL#flt={origin}.{dest}.{depart_date}"

def build_kayak_flights_url(origin: str, dest: str, depart_date: str, return_date: Optional[str] = None) -> str:
    """Gera link de busca direta no Kayak Voos para comparação e emissão."""
    if return_date:
        return f"https://www.kayak.com.br/flights/{origin}-{dest}/{depart_date}/{return_date}?sort=price_a"
    return f"https://www.kayak.com.br/flights/{origin}-{dest}/{depart_date}?sort=price_a"

def build_airline_url(airline: str) -> str:
    """Retorna link direto do portal da companhia aérea para emissão oficial."""
    al_lower = (airline or "").lower()
    if "gol" in al_lower:
        return "https://www.voegol.com.br"
    elif "latam" in al_lower:
        return "https://www.latamairlines.com/br/pt"
    elif "azul" in al_lower:
        return "https://www.voeazul.com.br"
    elif "tap" in al_lower:
        return "https://www.flytap.com/pt-br"
    elif "air france" in al_lower or "france" in al_lower:
        return "https://wwws.airfrance.com.br"
    elif "iberia" in al_lower:
        return "https://www.iberia.com/br"
    return ""

def search_single_flight(route: RouteConfig, date_str: str, max_retries: int = 2) -> Optional[FlightOffer]:
    """Busca a melhor opção de voo para uma rota em uma data específica (Ida ou Ida e Volta)."""
    origin = route.origin
    dest = route.destination
    is_round = route.is_round_trip

    return_date_str = None
    if is_round:
        depart_dt = datetime.date.fromisoformat(date_str)
        return_dt = depart_dt + datetime.timedelta(days=route.trip_duration_days)
        return_date_str = return_dt.strftime("%Y-%m-%d")

    for attempt in range(max_retries):
        try:
            if is_round and return_date_str:
                flight_queries = [
                    FlightQuery(date=date_str, from_airport=origin, to_airport=dest),
                    FlightQuery(date=return_date_str, from_airport=dest, to_airport=origin)
                ]
                trip_type = "round-trip"
            else:
                flight_queries = [FlightQuery(date=date_str, from_airport=origin, to_airport=dest)]
                trip_type = "one-way"

            q = create_query(
                flights=flight_queries,
                trip=trip_type,
                currency="BRL",
                language="pt-BR"
            )
            results = get_flights(q, integration=fetcher_instance)
            if not results or len(results) == 0:
                return None
            
            # Pega a melhor opção (menor preço total)
            best = results[0]
            if not hasattr(best, "price") or best.price is None:
                return None
            
            price_val = float(best.price)
            airline_name = best.airlines[0] if getattr(best, "airlines", None) else "Múltiplas Cias"
            stops = len(best.flights) - 1 if getattr(best, "flights", None) else 0
            
            link = q.url()
            kayak_link = build_kayak_flights_url(origin, dest, date_str, return_date_str)
            airline_link = build_airline_url(airline_name)
            
            return FlightOffer(
                origin=origin,
                destination=dest,
                origin_name=route.origin_name,
                dest_name=route.dest_name,
                flight_date=date_str,
                return_date=return_date_str,
                is_round_trip=is_round,
                price=price_val,
                airline=airline_name,
                stops=stops,
                deep_link=link,
                airline_link=airline_link,
                kayak_link=kayak_link
            )
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None

def generate_sample_dates(months_ahead: int = 10, count_per_month: int = 2) -> List[str]:
    """
    Gera uma grade estratégica de datas para os próximos meses:
    - Terças/Quartas (dias historicamente mais baratos para viajar)
    - Fins de semana
    Distribui ao longo de 6 a 12 meses.
    """
    dates = []
    today = datetime.date.today()
    
    # 1. Próximas 2 a 3 semanas (curto prazo)
    short_term = today + datetime.timedelta(days=15)
    dates.append(short_term.strftime("%Y-%m-%d"))
    
    # 2. Amostras para cada mês futuro
    for m in range(1, months_ahead + 1):
        target_month_date = today + datetime.timedelta(days=30 * m)
        year, month = target_month_date.year, target_month_date.month
        
        # Testa dia 10 e dia 20 do mês
        for day in [10, 20]:
            try:
                candidate = datetime.date(year, month, day)
                if candidate > today:
                    dates.append(candidate.strftime("%Y-%m-%d"))
            except ValueError:
                pass
                
    return sorted(list(set(dates)))

def scan_route_flexible(route: RouteConfig, sample_dates: List[str]) -> List[FlightOffer]:
    """Varre uma rota através de várias datas e registra os preços no banco."""
    offers: List[FlightOffer] = []
    
    for date_str in sample_dates:
        # Pausa amigável com jitter aleatório para respeitar o serviço
        time.sleep(random.uniform(0.8, 1.8))
        offer = search_single_flight(route, date_str)
        
        # Se não encontrou (ex: aeroportos regionais com dias específicos de voo), tenta dia seguinte
        if not offer and route.destination in ["URG", "GEL"]:
            next_day = (datetime.date.fromisoformat(date_str) + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            time.sleep(1.0)
            offer = search_single_flight(route, next_day)
            
        if offer:
            # Salva no banco de dados local
            database.save_flight_price(
                origin=offer.origin,
                destination=offer.destination,
                flight_date=offer.flight_date,
                return_date=offer.return_date or "",
                is_round_trip=offer.is_round_trip,
                price=offer.price,
                airline=offer.airline,
                stops=offer.stops,
                deep_link=offer.deep_link
            )
            
            # Verifica se é oportunidade para alerta
            avg = database.get_historical_average(offer.origin, offer.destination)
            if offer.price <= route.max_price_alert:
                offer.is_deal = True
                if avg and avg > offer.price:
                    offer.discount_pct = round(((avg - offer.price) / avg) * 100, 1)
            elif avg and offer.price <= avg * (1.0 - settings.DISCOUNT_THRESHOLD_PERCENT / 100.0):
                offer.is_deal = True
                offer.discount_pct = round(((avg - offer.price) / avg) * 100, 1)
                
            offers.append(offer)
            
    return offers
