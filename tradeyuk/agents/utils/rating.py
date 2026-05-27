"""Kosakata peringkat 5-tingkat bersama dan parser heuristik deterministik.

Skala lima tingkat yang sama (Beli, Overweight, Tahan, Underweight, Jual) digunakan oleh:
- Manajer Riset (rekomendasi rencana investasi)
- Manajer Portofolio (keputusan posisi final)
- Pemroses sinyal (peringkat yang diekstrak untuk konsumen hilir)
- Log memori (tag peringkat yang disimpan bersama setiap entri keputusan)

Memusatkannya di sini menghindari penyimpangan di antara titik-titik panggilan tersebut.
"""

from __future__ import annotations

import re
from typing import Tuple


# Skala 5-tingkat kanonis, terurut (paling bullish ke paling bearish).
RATINGS_5_TIER: Tuple[str, ...] = (
    "Beli", "Overweight", "Tahan", "Underweight", "Jual",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Matches "Rating: X" / "rating - X" / "Rating: **X**" — tolerates markdown
# bold wrappers and either a colon or hyphen separator.
_RATING_LABEL_RE = re.compile(r"rating.*?[:\-][\s*]*(\w+)", re.IGNORECASE)


def parse_rating(text: str, default: str = "Tahan") -> str:
    """Ekstrak peringkat 5-tingkat secara heuristik dari teks prosa.

    Strategi dua-lintasan:
    1. Cari label eksplisit "Rating: X" / "Peringkat: X" (toleran terhadap markdown bold).
    2. Jatuh kembali ke kata peringkat 5-tingkat pertama yang ditemukan di mana pun dalam teks.

    Mengembalikan string peringkat ber-kapitalisasi Title, atau ``default`` jika tidak ada kata peringkat yang muncul.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m and m.group(1).lower() in _RATING_SET:
            return m.group(1).capitalize()

    for line in text.splitlines():
        for word in line.lower().split():
            clean = word.strip("*:.,")
            if clean in _RATING_SET:
                return clean.capitalize()

    return default
