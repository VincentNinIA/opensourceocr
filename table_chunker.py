"""
Module pour détecter et extraire les tableaux d'une image avant l'OCR.
Utilise PaddleOCR pour la détection de layout et découpe les tableaux.
"""

import os
import re
import base64
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Désactiver la vérification de connectivité pour accélérer le démarrage
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import cv2
import numpy as np
from paddleocr import PPStructureV3


# -----------------------------
# Utils image
# -----------------------------
def crop_with_padding(img: np.ndarray, bbox: List[int], pad: int = 20) -> np.ndarray:
    """Découpe une région avec padding"""
    x1, y1, x2, y2 = bbox
    h, w = img.shape[:2]
    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(w, x2 + pad)
    y2p = min(h, y2 + pad)
    return img[y1p:y2p, x1p:x2p].copy()


def upscale(img: np.ndarray, factor: float = 2.0) -> np.ndarray:
    """Agrandit l'image pour améliorer l'OCR"""
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_CUBIC)


def to_png_bytes(img: np.ndarray) -> bytes:
    """Encode l'image en PNG bytes"""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Failed to encode crop as PNG.")
    return buf.tobytes()


def image_to_base64(img: np.ndarray) -> str:
    """Convertit une image numpy en base64 string"""
    png_bytes = to_png_bytes(img)
    return base64.b64encode(png_bytes).decode('utf-8')


# -----------------------------
# Détection de tableaux
# -----------------------------
@dataclass
class TableRegion:
    """Représente une région de tableau détectée"""
    bbox: List[int]  # [x1, y1, x2, y2]
    crop: np.ndarray
    crop_base64: str
    index: int


def detect_tables(image_bytes: bytes, upscale_factor: float = 1.5, padding: int = 30) -> List[TableRegion]:
    """
    Détecte les tableaux dans une image en utilisant PaddleOCR PP-Structure.

    Args:
        image_bytes: Image en bytes
        upscale_factor: Facteur d'agrandissement pour améliorer l'OCR
        padding: Padding autour des tableaux détectés

    Returns:
        Liste de TableRegion avec les crops des tableaux détectés
    """
    # Charger l'image depuis les bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Impossible de décoder l'image")

    # Initialiser PP-Structure pour la détection de layout avec paramètres légers
    # use_angle_cls=False pour désactiver la classification d'angle (économise mémoire)
    # lang='en' pour modèle anglais uniquement (plus léger que multi-langue)
    engine = PPStructureV3(
        use_angle_cls=False,
        lang='en',
        use_gpu=False
    )

    # Détecter les régions
    results = engine.predict(img)

    # Filtrer uniquement les tableaux
    table_regions = []
    for i, result in enumerate(results):
        if str(result.get("type", "")).lower() == "table":
            bbox = [int(x) for x in result["bbox"]]

            # Découper avec padding
            crop = crop_with_padding(img, bbox, pad=padding)

            # Agrandir si demandé
            if upscale_factor > 1.0:
                crop = upscale(crop, factor=upscale_factor)

            # Convertir en base64
            crop_b64 = image_to_base64(crop)

            table_regions.append(TableRegion(
                bbox=bbox,
                crop=crop,
                crop_base64=crop_b64,
                index=i
            ))

    return table_regions


def extract_markdown_tables(markdown: str) -> List[List[List[str]]]:
    """
    Extrait les tableaux markdown d'un texte.
    Retourne une liste de tableaux; chaque tableau = liste de lignes; ligne = liste de cellules.
    """
    lines = [ln.rstrip() for ln in markdown.splitlines()]
    tables: List[List[List[str]]] = []

    current: List[str] = []
    for ln in lines:
        if ln.strip().startswith("|") and ln.count("|") >= 2:
            current.append(ln)
        else:
            if current:
                tables.append(_parse_md_table_block(current))
                current = []
    if current:
        tables.append(_parse_md_table_block(current))

    # Supprimer les tableaux vides
    tables = [t for t in tables if t and any(any(c.strip() for c in r) for r in t)]
    return tables


def _parse_md_table_block(block_lines: List[str]) -> List[List[str]]:
    """Parse un bloc de lignes markdown en tableau"""
    rows: List[List[str]] = []
    for ln in block_lines:
        # Ignorer la ligne de séparation
        if re.match(r"^\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$", ln.strip()):
            continue
        parts = [p.strip() for p in ln.strip().strip("|").split("|")]
        rows.append(parts)
    return rows


# -----------------------------
# Validation des tableaux
# -----------------------------
CHEM_HEADER_TOKENS = {"c %", "cr %", "ni %", "mo %", "mn %", "si %", "p %", "n %", "cu %", "co %", "ti %"}
MECH_HEADER_TOKENS = {"rp", "rm", "a5", "hb", "re", "yield", "tensile"}


def normalize_token(s: str) -> str:
    """Normalise un token pour la comparaison"""
    return re.sub(r"\s+", " ", s.strip().lower())


def guess_table_type(table: List[List[str]]) -> str:
    """Devine le type de tableau (chemistry, mechanical, generic)"""
    if not table:
        return "unknown"
    header = " ".join(normalize_token(x) for x in table[0])
    if any(tok in header for tok in CHEM_HEADER_TOKENS):
        return "chemistry"
    if any(tok in header for tok in MECH_HEADER_TOKENS):
        return "mechanical"
    return "generic"


def stable_column_count(table: List[List[str]], min_rows: int = 3) -> bool:
    """Vérifie que le tableau a un nombre de colonnes stable"""
    if len(table) < min_rows:
        return True
    counts = [len(r) for r in table if any(c.strip() for c in r)]
    if not counts:
        return True
    mode = max(set(counts), key=counts.count)
    ok = sum(1 for c in counts if abs(c - mode) <= 1) / len(counts) >= 0.8
    return ok
