"""
Rastreador de promoções relâmpago, cupons de desconto e feirões aéreos (RSS e Feeds).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
import feedparser
import database

FEEDS = [
    ("Melhores Destinos", "https://www.melhoresdestinos.com.br/feed"),
    ("Passagens Imperdíveis", "https://www.passagensimperdiveis.com.br/feed/"),
]

# Termos-chave de interesse para filtrar as 12 rotas e locação de carros
KEYWORDS = [
    "curitiba", "boa vista", "rio de janeiro", "porto alegre", "uruguaiana",
    "joão pessoa", "joao pessoa", "fortaleza", "nova york", "nova iorque", "miami",
    "madrid", "madri", "lisboa", "portugal", "paris", "frança", "franca", "santo ângelo", "santo angelo",
    "aluguel de carro", "aluguel de veículos", "locação de veículos", "rentcars",
    "localiza", "movida", "unidas", "cupom", "feirão", "promocao relampago", "erro de tarifa"
]

@dataclass
class PromoItem:
    source: str
    title: str
    link: str
    snippet: str
    published_at: str
    relevant_keyword: str

def clean_html(text: str) -> str:
    """Remove tags HTML e normaliza espaços."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def scan_promotions() -> List[PromoItem]:
    """Varre os feeds de notícias de viagens e retorna promoções novas e relevantes."""
    new_promos: List[PromoItem] = []
    
    for source_name, feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = getattr(entry, "title", "")
                link = getattr(entry, "link", "")
                summary = getattr(entry, "summary", "")
                published = getattr(entry, "published", "")
                
                content_lower = f"{title.lower()} {summary.lower()}"
                
                # Checa se menciona alguma das nossas cidades ou aluguel de carros
                matched_kw = None
                for kw in KEYWORDS:
                    if kw in content_lower:
                        matched_kw = kw
                        break
                        
                if matched_kw:
                    clean_summary = clean_html(summary)[:250] + ("..." if len(summary) > 250 else "")
                    is_new = database.save_promotion(
                        source=source_name,
                        title=title,
                        link=link,
                        snippet=clean_summary,
                        published_at=published
                    )
                    if is_new:
                        new_promos.append(PromoItem(
                            source=source_name,
                            title=title,
                            link=link,
                            snippet=clean_summary,
                            published_at=published,
                            relevant_keyword=matched_kw
                        ))
        except Exception:
            continue
            
    return new_promos
