"""
Mecanismo de busca e cotação de locação de veículos nos destinos monitorados.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
import httpx
from config import CAR_RENTAL_DESTINATIONS
import database

@dataclass
class CarRentalDeal:
    destination_code: str
    city_name: str
    country: str
    pickup_date: str
    return_date: str
    days: int
    estimated_daily_price: float
    estimated_total_price: float
    currency: str
    provider_recommendation: str
    comparator_link: str
    rentcars_link: str
    booking_link: str = ""
    promo_tip: str = ""

# URLs oficiais e diretas por aeroporto no Rentcars para evitar redirecionamento genérico
RENTCARS_AIRPORT_URLS: Dict[str, str] = {
    "CWB": "https://www.rentcars.com/pt-br/aeroportos/brasil/cwb-afonso-pena-curitiba-parana",
    "GIG": "https://www.rentcars.com/pt-br/aeroportos/brasil/gig-galeao-rio-de-janeiro-rio-de-janeiro",
    "POA": "https://www.rentcars.com/pt-br/aeroportos/brasil/poa-salgado-filho-porto-alegre-rio-grande-do-sul",
    "URG": "https://www.rentcars.com/pt-br/aeroportos/brasil/urg-rubem-berta-uruguaiana-rio-grande-do-sul",
    "JPA": "https://www.rentcars.com/pt-br/aeroportos/brasil/jpa-presidente-castro-pinto-joao-pessoa-paraiba",
    "FOR": "https://www.rentcars.com/pt-br/aeroportos/brasil/for-pinto-martins-fortaleza-ceara",
    "BVB": "https://www.rentcars.com/pt-br/aeroportos/brasil/bvb-atlas-brasil-cantanhede-boa-vista-roraima",
    "GEL": "https://www.rentcars.com/pt-br/aeroportos/brasil/gel-santo-angelo-santo-angelo-rio-grande-do-sul",
    "JFK": "https://www.rentcars.com/pt-br/aeroportos/estados-unidos/jfk-john-f-kennedy-internacional-nova-iorque-nova-iorque",
    "MIA": "https://www.rentcars.com/pt-br/aeroportos/estados-unidos/mia-miami-internacional-miami-florida",
    "MAD": "https://www.rentcars.com/pt-br/aeroportos/espanha/mad-adolfo-suarez-barajas-madrid-madrid",
    "LIS": "https://www.rentcars.com/pt-br/aeroportos/portugal/lis-humberto-delgado-lisboa-lisboa",
    "CDG": "https://www.rentcars.com/pt-br/aeroportos/franca/cdg-charles-de-gaulle-paris-ilha-de-franca",
}

def generate_rental_links(dest_code: str, pickup_date: str, return_date: str) -> Dict[str, str]:
    """
    Gera links diretos e parametrizados de reserva e comparação com locais e datas pré-carregados.
    """
    # 1. Booking.com / Rentalcars - Busca direta por código IATA e datas/horários para emissão e reserva
    booking_url = (
        f"https://www.booking.com/cars/index.pt-br.html?"
        f"pu_loc_iata={dest_code}&do_loc_iata={dest_code}&pu_time={pickup_date}T10:00&do_time={return_date}T10:00"
    )
    
    # 2. Kayak - Comparador com aeroporto, datas e horário pré-configurados
    kayak_url = f"https://www.kayak.com.br/cars/{dest_code}/{pickup_date}/{return_date}/10h/10h"
    
    # 3. Rentcars - Página oficial do aeroporto específico do destino
    rentcars_url = RENTCARS_AIRPORT_URLS.get(
        dest_code,
        f"https://www.rentcars.com/pt-br/cidades/brasil/{dest_code.lower()}"
    )
    
    return {
        "booking": booking_url,
        "kayak": kayak_url,
        "rentcars": rentcars_url
    }

# Tarifas médias de referência de mercado (benchmark diária econômica em reais/moeda local)
REFERENCE_DAILY_RATES: Dict[str, Dict[str, float]] = {
    "CWB": {"base_brl": 95.0, "deal_threshold": 80.0},
    "GIG": {"base_brl": 110.0, "deal_threshold": 95.0},
    "POA": {"base_brl": 105.0, "deal_threshold": 90.0},
    "URG": {"base_brl": 140.0, "deal_threshold": 120.0},
    "JPA": {"base_brl": 115.0, "deal_threshold": 98.0},
    "FOR": {"base_brl": 110.0, "deal_threshold": 92.0},
    "BVB": {"base_brl": 150.0, "deal_threshold": 130.0},
    "GEL": {"base_brl": 160.0, "deal_threshold": 135.0},
    "JFK": {"base_usd": 48.0, "deal_threshold": 38.0},
    "MIA": {"base_usd": 32.0, "deal_threshold": 24.0},
    "MAD": {"base_eur": 22.0, "deal_threshold": 16.0},
    "LIS": {"base_eur": 24.0, "deal_threshold": 17.0},
    "CDG": {"base_eur": 29.0, "deal_threshold": 21.0},
}

PROMO_TIPS: Dict[str, str] = {
    "MIA": "Flórida tem diárias muito competitivas! Evite pagar pedágio na locadora (use SunPass próprio ou pague na via).",
    "MAD": "Espanha tem excelentes tarifas na RecordGo, Centauro e Goldcar. Reserve com seguro cancelável.",
    "LIS": "Portugal tem operadoras locais como Guerin e Drive on Holidays com diárias econômicas a partir de 15€.",
    "JFK": "Em NY o aluguel no JFK/EWR tem taxas aeroportuárias mais altas. Compare retirada fora do terminal se for viável.",
    "BVB": "Boa Vista tem frota mais reduzida, reservar com antecedência na Localiza ou Unidas garante disponibilidade.",
    "URG": "Uruguaiana possui poucas locadoras no aeroporto, consulte disponibilidade prévia.",
    "GEL": "Santo Ângelo opera principalmente com Localiza/Unidas no centro/aeroporto.",
    "CWB": "Em Curitiba, Localiza, Movida e Unidas têm tarifas promocionais com seguro básico incluso na Rentcars.",
}

def check_car_rentals_for_destination(dest_code: str, pickup_date: Optional[str] = None, return_date: Optional[str] = None) -> CarRentalDeal:
    """Gera a cotação e links promocionais para um destino específico."""
    info = CAR_RENTAL_DESTINATIONS.get(dest_code, {"city": dest_code, "country": "Geral", "currency": "BRL"})
    
    today = datetime.date.today()
    if not pickup_date:
        # Padrão: daqui a 45 dias
        p_dt = today + datetime.timedelta(days=45)
        pickup_date = p_dt.strftime("%Y-%m-%d")
    else:
        p_dt = datetime.date.fromisoformat(pickup_date)
        
    if not return_date:
        # Período de 5 dias
        r_dt = p_dt + datetime.timedelta(days=5)
        return_date = r_dt.strftime("%Y-%m-%d")
    else:
        r_dt = datetime.date.fromisoformat(return_date)
        
    days = max(1, (r_dt - p_dt).days)
    currency = info.get("currency", "BRL")
    
    ref = REFERENCE_DAILY_RATES.get(dest_code, {})
    if currency == "USD":
        daily_rate = ref.get("base_usd", 45.0)
    elif currency == "EUR":
        daily_rate = ref.get("base_eur", 25.0)
    else:
        daily_rate = ref.get("base_brl", 110.0)
        
    total_rate = round(daily_rate * days, 2)
    links = generate_rental_links(dest_code, pickup_date, return_date)
    
    # Provedor recomendado conforme a localidade
    if info.get("country") == "Brasil":
        provider = "Localiza / Movida / Rentcars (Sem IOF, parcelamento)"
    elif info.get("country") == "EUA":
        provider = "Alamo / Hertz / Budget via Rentcars ou Kayak"
    else:
        provider = "Europcar / Sixt / Centauro via Rentcars ou Kayak"
        
    deal = CarRentalDeal(
        destination_code=dest_code,
        city_name=info["city"],
        country=info["country"],
        pickup_date=pickup_date,
        return_date=return_date,
        days=days,
        estimated_daily_price=daily_rate,
        estimated_total_price=total_rate,
        currency=currency,
        provider_recommendation=provider,
        comparator_link=links["kayak"],
        rentcars_link=links["rentcars"],
        booking_link=links["booking"],
        promo_tip=PROMO_TIPS.get(dest_code, "Dica: reservando com antecedência garante melhor disponibilidade e parcelamento sem IOF.")
    )
    
    # Salva no histórico do banco com link parametrizado para reserva imediata
    database.save_car_rental(
        destination_code=dest_code,
        pickup_date=pickup_date,
        return_date=return_date,
        estimated_daily_price=daily_rate,
        provider=provider,
        deep_link=links["booking"]
    )
    
    return deal

def check_all_car_destinations() -> List[CarRentalDeal]:
    """Retorna cotações e links atualizados para todos os destinos monitorados."""
    results = []
    for code in CAR_RENTAL_DESTINATIONS.keys():
        deal = check_car_rentals_for_destination(code)
        results.append(deal)
    return results
