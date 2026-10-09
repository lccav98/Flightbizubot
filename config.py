"""
Configurações do Radar de Viagens e Locação de Veículos 24/7.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class RouteConfig:
    origin: str
    destination: str
    origin_name: str
    dest_name: str
    max_price_alert: float  # Preço teto para alerta imediato (BRL)
    is_round_trip: bool = False  # Ida e volta
    trip_duration_days: int = 5  # Duração padrão da estadia (dias)
    is_international: bool = False
    aliases_dest: List[str] = field(default_factory=list)

# 12 trechos monitorados (Rotas a partir de Curitiba configuradas como IDA E VOLTA)
DEFAULT_ROUTES: List[RouteConfig] = [
    RouteConfig(
        origin="BVB",
        destination="CWB",
        origin_name="Boa Vista - RR",
        dest_name="Curitiba - PR",
        max_price_alert=2800.0,
        is_round_trip=True,
        trip_duration_days=7,
        is_international=False
    ),
    RouteConfig(
        origin="CWB",
        destination="GIG",
        origin_name="Curitiba - PR",
        dest_name="Rio de Janeiro - RJ",
        max_price_alert=850.0,
        is_round_trip=True,
        trip_duration_days=5,
        is_international=False,
        aliases_dest=["SDU", "GIG"]
    ),
    RouteConfig(
        origin="CWB",
        destination="POA",
        origin_name="Curitiba - PR",
        dest_name="Porto Alegre - RS",
        max_price_alert=750.0,
        is_round_trip=True,
        trip_duration_days=4,
        is_international=False
    ),
    RouteConfig(
        origin="CWB",
        destination="URG",
        origin_name="Curitiba - PR",
        dest_name="Uruguaiana - RS",
        max_price_alert=1500.0,
        is_round_trip=True,
        trip_duration_days=5,
        is_international=False
    ),
    RouteConfig(
        origin="CWB",
        destination="JPA",
        origin_name="Curitiba - PR",
        dest_name="João Pessoa - PB",
        max_price_alert=1650.0,
        is_round_trip=True,
        trip_duration_days=6,
        is_international=False
    ),
    RouteConfig(
        origin="CWB",
        destination="FOR",
        origin_name="Curitiba - PR",
        dest_name="Fortaleza - CE",
        max_price_alert=1600.0,
        is_round_trip=True,
        trip_duration_days=6,
        is_international=False
    ),
    RouteConfig(
        origin="CWB",
        destination="JFK",
        origin_name="Curitiba - PR",
        dest_name="Nova Iorque - EUA",
        max_price_alert=4200.0,
        is_round_trip=True,
        trip_duration_days=10,
        is_international=True,
        aliases_dest=["JFK", "EWR"]
    ),
    RouteConfig(
        origin="CWB",
        destination="MIA",
        origin_name="Curitiba - PR",
        dest_name="Miami - EUA",
        max_price_alert=3800.0,
        is_round_trip=True,
        trip_duration_days=10,
        is_international=True
    ),
    RouteConfig(
        origin="CWB",
        destination="MAD",
        origin_name="Curitiba - PR",
        dest_name="Madrid - ESP",
        max_price_alert=4600.0,
        is_round_trip=True,
        trip_duration_days=12,
        is_international=True
    ),
    RouteConfig(
        origin="CWB",
        destination="LIS",
        origin_name="Curitiba - PR",
        dest_name="Lisboa - POR",
        max_price_alert=4600.0,
        is_round_trip=True,
        trip_duration_days=12,
        is_international=True
    ),
    RouteConfig(
        origin="CWB",
        destination="CDG",
        origin_name="Curitiba - PR",
        dest_name="Paris - FRA",
        max_price_alert=4800.0,
        is_round_trip=True,
        trip_duration_days=12,
        is_international=True,
        aliases_dest=["CDG", "ORY"]
    ),
    RouteConfig(
        origin="CWB",
        destination="GEL",
        origin_name="Curitiba - PR",
        dest_name="Santo Ângelo - RS",
        max_price_alert=1800.0,
        is_round_trip=True,
        trip_duration_days=5,
        is_international=False
    ),
]

# Destinos para monitoramento de locação de veículos
CAR_RENTAL_DESTINATIONS: Dict[str, Dict[str, str]] = {
    "CWB": {"city": "Curitiba", "country": "Brasil", "currency": "BRL"},
    "GIG": {"city": "Rio de Janeiro", "country": "Brasil", "currency": "BRL"},
    "POA": {"city": "Porto Alegre", "country": "Brasil", "currency": "BRL"},
    "URG": {"city": "Uruguaiana", "country": "Brasil", "currency": "BRL"},
    "JPA": {"city": "João Pessoa", "country": "Brasil", "currency": "BRL"},
    "FOR": {"city": "Fortaleza", "country": "Brasil", "currency": "BRL"},
    "BVB": {"city": "Boa Vista", "country": "Brasil", "currency": "BRL"},
    "GEL": {"city": "Santo Ângelo", "country": "Brasil", "currency": "BRL"},
    "JFK": {"city": "Nova Iorque", "country": "EUA", "currency": "USD"},
    "MIA": {"city": "Miami", "country": "EUA", "currency": "USD"},
    "MAD": {"city": "Madrid", "country": "Espanha", "currency": "EUR"},
    "LIS": {"city": "Lisboa", "country": "Portugal", "currency": "EUR"},
    "CDG": {"city": "Paris", "country": "França", "currency": "EUR"},
}

class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Intervalo de varredura (em minutos)
    SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
    
    # Sensibilidade de desconto para alerta (% abaixo da média histórica)
    DISCOUNT_THRESHOLD_PERCENT: float = float(os.getenv("DISCOUNT_THRESHOLD_PERCENT", "20.0"))

    # Quantidade de meses para frente a serem monitorados (6 a 12 meses)
    MONTHS_AHEAD: int = int(os.getenv("MONTHS_AHEAD", "10"))

    # Banco de dados
    DB_PATH: str = os.getenv("DB_PATH", "radar_viagens.db")

settings = Settings()
