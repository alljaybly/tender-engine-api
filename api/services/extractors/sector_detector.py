"""
Sector detection via keyword matching in tender document text.

Detects common South African tender sectors:
cleaning, construction, electrical, security, gardening,
it_services, maintenance, supply, general.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Sector keywords: (sector_name, weighted keywords)
_SECTOR_KEYWORDS = {
    "cleaning": [
        "cleaning", "janitorial", "sanitary", "hygiene", "washroom",
        "floor care", "carpet cleaning", "window cleaning", "disinfection",
        "office cleaning", "industrial cleaning", "deep clean",
    ],
    "construction": [
        "construction", "building", "civil works", "road", "bridge",
        "earthworks", "excavation", "concrete", "steel", "structural",
        "paving", "trenching", "foundation", "renovation", "rehabilitation",
    ],
    "electrical": [
        "electrical", "electrification", "cabling", "wiring", "substation",
        "transformer", "generator", "solar", "photovoltaic", "lighting",
        "switchgear", "distribution board", "power supply",
    ],
    "security": [
        "security", "guard", "patrol", "access control", "cctv",
        "surveillance", "alarm", "perimeter", "armed response",
        "security services", "protect",
    ],
    "gardening": [
        "gardening", "landscaping", "lawn", "tree", "horticulture",
        "irrigation", "pruning", "weed", "grass cutting",
    ],
    "it_services": [
        "it services", "information technology", "software", "hardware",
        "network", "cyber", "server", "cloud", "website", "web development",
        "it support", "managed services", "digital",
    ],
    "maintenance": [
        "maintenance", "repair", "servicing", "upkeep", "facilities management",
        "preventative maintenance", "planned maintenance",
    ],
    "supply": [
        "supply and delivery", "supply of", "provision of", "furniture",
        "equipment supply", "stationery", "consumables", "personal protective equipment",
        "ppe", "uniform", "tools and equipment",
    ],
    "general": [
        "general services", "consulting", "training", "logistics",
        "transport", "freight", "catering", "event management",
        "professional services", "feasibility study",
    ],
}


def detect_sector(text: str) -> Optional[str]:
    """
    Analyse document text and return the most likely sector.

    Uses weighted keyword matching — each keyword match contributes
    to a sector score.  Returns the sector with the highest score,
    or None if no sector is recognisable.
    """
    if not text or not text.strip():
        logger.debug("[SECTOR] Empty text, cannot detect sector")
        return None

    lower_text = text.lower()
    scores: dict[str, int] = {}

    for sector, keywords in _SECTOR_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            # Count occurrences (not just presence)
            count = len(re.findall(re.escape(keyword), lower_text))
            score += count
        if score > 0:
            scores[sector] = score
            logger.debug("[SECTOR] %s score=%d", sector, score)

    if not scores:
        logger.info("[SECTOR] No sector detected in document")
        return None

    # Return highest-scoring sector
    best_sector = max(scores, key=scores.get)
    logger.info(
        "[SECTOR] Detected sector=%s score=%d",
        best_sector, scores[best_sector],
    )
    return best_sector