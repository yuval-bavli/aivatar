"""ARPABET phoneme -> Azure viseme ID (0-14) mapping table."""
from typing import Dict

# Azure viseme IDs 0-14, matching the HTML prototype and Unity AzureSpeechManager
ARPABET_TO_VISEME: Dict[str, int] = {
    # 0 - sil (silence / near-silence)
    'SIL': 0,  'SP': 0,  'HH': 0,

    # 1 - PP (bilabial)
    'P': 1,  'B': 1,  'M': 1,

    # 2 - FF (labiodental)
    'F': 2,  'V': 2,

    # 3 - TH (dental)
    'TH': 3,  'DH': 3,

    # 4 - DD (alveolar stop)
    'T': 4,  'D': 4,

    # 5 - kk (velar)
    'K': 5,  'G': 5,

    # 6 - CH (postalveolar)
    'CH': 6,  'JH': 6,  'SH': 6,  'ZH': 6,

    # 7 - SS (sibilant)
    'S': 7,  'Z': 7,

    # 8 - nn (nasal)
    'N': 8,  'NG': 8,
    # L is a tongue gesture, not a lip gesture — map to neutral so it doesn't
    # create a visible mid-vowel dip (e.g. the double-open in "Hello")
    'L': 0,

    # 9 - RR (rhotic)
    'R': 9,  'ER': 9,

    # 10 - aa (low/open vowel)
    'AA': 10,  'AE': 10,  'AH': 10,

    # 11 - E (mid-front vowel)
    'EH': 11,  'EY': 11,

    # 12 - ih (high-front vowel)
    'IH': 12,  'IY': 12,  'Y': 12,

    # 13 - oh (mid-back rounded vowel)
    'AO': 13,  'OW': 13,  'AW': 13,

    # 14 - ou (high-back / rounded)
    'UW': 14,  'UH': 14,  'OY': 14,  'W': 14,
}

# Phoneme categories for enhanced timing weights
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
STOPS = {'P', 'B', 'T', 'D', 'K', 'G'}
FRICATIVES = {'F', 'V', 'TH', 'DH', 'S', 'Z', 'SH', 'ZH'}
AFFRICATES = {'CH', 'JH'}
NASALS = {'M', 'N', 'NG'}
LIQUIDS = {'L', 'R'}
GLIDES = {'W', 'Y'}

PHONEME_WEIGHT: Dict[str, float] = {}
for p in VOWELS:
    PHONEME_WEIGHT[p] = 1.5
for p in STOPS:
    PHONEME_WEIGHT[p] = 0.6
for p in FRICATIVES:
    PHONEME_WEIGHT[p] = 1.1
for p in AFFRICATES:
    PHONEME_WEIGHT[p] = 0.9
for p in NASALS:
    PHONEME_WEIGHT[p] = 1.0
for p in LIQUIDS:
    PHONEME_WEIGHT[p] = 1.0
for p in GLIDES:
    PHONEME_WEIGHT[p] = 0.8


def phoneme_to_viseme(phoneme: str) -> int:
    """Map an ARPABET phoneme (no stress digits) to an Azure viseme ID 0-14."""
    return ARPABET_TO_VISEME.get(phoneme.upper(), 0)
