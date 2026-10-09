"""
Gerenciamento do banco de dados SQLite local para histórico de preços e alertas.
"""
from __future__ import annotations

import sqlite3
import datetime
from typing import List, Dict, Any, Optional
from config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Histórico de preços de voos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flight_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                return_date TEXT,
                is_round_trip INTEGER DEFAULT 1,
                price REAL NOT NULL,
                airline TEXT,
                stops INTEGER DEFAULT 0,
                deep_link TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flight_lookup ON flight_prices(origin, destination, flight_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flight_recorded ON flight_prices(recorded_at)")

        # Migração automática de colunas se banco já existia
        cursor.execute("PRAGMA table_info(flight_prices)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "return_date" not in existing_cols:
            cursor.execute("ALTER TABLE flight_prices ADD COLUMN return_date TEXT")
        if "is_round_trip" not in existing_cols:
            cursor.execute("ALTER TABLE flight_prices ADD COLUMN is_round_trip INTEGER DEFAULT 1")


        # Histórico de cotações e links de aluguel de carros
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS car_rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_code TEXT NOT NULL,
                pickup_date TEXT NOT NULL,
                return_date TEXT NOT NULL,
                estimated_daily_price REAL,
                currency TEXT DEFAULT 'BRL',
                provider TEXT,
                deep_link TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Registro de alertas já enviados (para evitar flood/spam)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                lookup_key TEXT NOT NULL,
                last_price REAL NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_key ON alerts_sent(lookup_key)")

        # Promoções relâmpago e notícias capturadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                snippet TEXT,
                published_at TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Usuários inscritos para receber alertas e interagir (multi-usuário)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inscreve o chat_id do dono configurado no .env automaticamente se existir
        if settings.TELEGRAM_CHAT_ID:
            cursor.execute("""
                INSERT INTO subscribers (chat_id, first_name, is_active)
                VALUES (?, 'Admin', 1)
                ON CONFLICT(chat_id) DO UPDATE SET is_active = 1
            """, (str(settings.TELEGRAM_CHAT_ID),))
        
        conn.commit()

def save_flight_price(origin: str, destination: str, flight_date: str, price: float, airline: str, stops: int, deep_link: str = "", return_date: str = "", is_round_trip: bool = True):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO flight_prices (origin, destination, flight_date, return_date, is_round_trip, price, airline, stops, deep_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (origin, destination, flight_date, return_date, 1 if is_round_trip else 0, price, airline, stops, deep_link))
        conn.commit()

def get_historical_average(origin: str, destination: str) -> Optional[float]:
    """Retorna o preço médio histórico registrado para a rota."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(price) as avg_price, COUNT(*) as cnt 
            FROM flight_prices 
            WHERE origin = ? AND destination = ?
        """, (origin, destination))
        row = cursor.fetchone()
        if row and row["cnt"] >= 3:
            return float(row["avg_price"])
        return None

def get_lowest_price(origin: str, destination: str) -> Optional[Dict[str, Any]]:
    """Retorna o menor preço histórico já encontrado para a rota."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT price, flight_date, return_date, is_round_trip, airline, stops, deep_link, recorded_at
            FROM flight_prices 
            WHERE origin = ? AND destination = ?
            ORDER BY price ASC 
            LIMIT 1
        """, (origin, destination))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_lowest_prices() -> List[Dict[str, Any]]:
    """Retorna um sumário com o menor preço já encontrado para cada rota."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT origin, destination, MIN(price) as min_price, flight_date, return_date, is_round_trip, airline, deep_link, recorded_at
            FROM flight_prices
            GROUP BY origin, destination
            ORDER BY min_price ASC
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        for r in rows:
            if not r.get("deep_link") or "travel/flights?q=" in r["deep_link"]:
                from flight_engine import build_google_flights_url
                r["deep_link"] = build_google_flights_url(r["origin"], r["destination"], r["flight_date"], r.get("return_date"))
        return rows


def should_send_flight_alert(origin: str, destination: str, flight_date: str, price: float, max_threshold: float) -> bool:
    """
    Decide se deve disparar alerta:
    1. Preço abaixo do teto configurado OU
    2. Mais de 20% abaixo da média histórica.
    E verifica se o alerta para esta mesma data já não foi disparado recentemente por um preço similar.
    """
    key = f"flight:{origin}:{destination}:{flight_date}"
    avg = get_historical_average(origin, destination)
    
    is_deal = False
    if price <= max_threshold:
        is_deal = True
    elif avg and price <= avg * (1.0 - settings.DISCOUNT_THRESHOLD_PERCENT / 100.0):
        is_deal = True

    if not is_deal:
        return False

    with get_connection() as conn:
        cursor = conn.cursor()
        # Verificar último alerta enviado para essa mesma chave nas últimas 24 horas
        cursor.execute("""
            SELECT last_price, sent_at 
            FROM alerts_sent 
            WHERE lookup_key = ? 
            ORDER BY sent_at DESC 
            LIMIT 1
        """, (key,))
        row = cursor.fetchone()
        if row:
            last_price = float(row["last_price"])
            # Só reenvia se o preço caiu ainda mais (pelo menos 5% a menos que o alerta anterior)
            if price >= last_price * 0.95:
                return False

    return True

def mark_alert_sent(alert_type: str, lookup_key: str, price: float):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts_sent (alert_type, lookup_key, last_price)
            VALUES (?, ?, ?)
        """, (alert_type, lookup_key, price))
        conn.commit()

def save_car_rental(destination_code: str, pickup_date: str, return_date: str, estimated_daily_price: float, provider: str, deep_link: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO car_rentals (destination_code, pickup_date, return_date, estimated_daily_price, provider, deep_link)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (destination_code, pickup_date, return_date, estimated_daily_price, provider, deep_link))
        conn.commit()

def save_promotion(source: str, title: str, link: str, snippet: str = "", published_at: str = "") -> bool:
    """Salva uma promoção se for nova. Retorna True se foi inserida, False se já existia."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO promotions (source, title, link, snippet, published_at)
                VALUES (?, ?, ?, ?, ?)
            """, (source, title, link, snippet, published_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_recent_promotions(limit: int = 5) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source, title, link, snippet, published_at, recorded_at
            FROM promotions
            ORDER BY recorded_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def register_or_update_subscriber(chat_id: str, username: str = "", first_name: str = "") -> bool:
    """Registra novo assinante ou atualiza sua data de última interação."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subscribers (chat_id, username, first_name, is_active, last_interaction)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                username = CASE WHEN excluded.username != '' THEN excluded.username ELSE subscribers.username END,
                first_name = CASE WHEN excluded.first_name != '' THEN excluded.first_name ELSE subscribers.first_name END,
                is_active = 1,
                last_interaction = CURRENT_TIMESTAMP
        """, (str(chat_id), username or "", first_name or ""))
        conn.commit()
        return True

def set_subscriber_status(chat_id: str, is_active: bool):
    """Ativa ou desativa um assinante."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE subscribers 
            SET is_active = ?, last_interaction = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (1 if is_active else 0, str(chat_id)))
        conn.commit()

def is_subscriber_active(chat_id: str) -> bool:
    """Verifica se o usuário está com alertas ativos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM subscribers WHERE chat_id = ?", (str(chat_id),))
        row = cursor.fetchone()
        return bool(row and row["is_active"] == 1)

def get_active_subscribers() -> List[str]:
    """Retorna a lista de chat_ids de todos os assinantes ativos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM subscribers WHERE is_active = 1")
        rows = cursor.fetchall()
        return [str(row["chat_id"]) for row in rows]

def count_active_subscribers() -> int:
    """Retorna o número total de assinantes ativos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM subscribers WHERE is_active = 1")
        row = cursor.fetchone()
        return int(row["total"]) if row else 0

