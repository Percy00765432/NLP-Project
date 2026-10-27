"""
Multilingual & Code-Mixed Financial Text Preprocessor.

Handles:
1. Script & Language Detection (English, Hindi, Tamil, Telugu, Bengali, Kannada, and Hinglish/Code-Mixed)
2. Financial Token Normalization (Currency, Account Masks, Dates, VPA handles)
3. Code-Mixed & Transliterated Token Normalization (mapping common Romanized Indian banking terms to canonical tags)
4. Text Cleaning for ML/Transformer representations
"""

import re
from typing import Dict, Any, Tuple


# Unicode ranges for Indian scripts
SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi)
    "bn": (0x0980, 0x09FF),  # Bengali
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "te": (0x0C00, 0x0C7F),  # Telugu
    "kn": (0x0C80, 0x0CFF),  # Kannada
}

# Common Romanized Indian / Code-mixed words in financial messages (Hinglish, Tanglish, Kanglish)
CODE_MIXED_LEXICON = {
    "mein": "in",
    "me": "in",
    "se": "from",
    "ko": "to",
    "ka": "of",
    "ki": "of",
    "ke": "of",
    "hua": "happened",
    "hui": "happened",
    "gaya": "went",
    "gaye": "went",
    "aaya": "came",
    "aaye": "came",
    "mila": "received",
    "mile": "received",
    "bheja": "sent",
    "bheje": "sent",
    "khata": "account",
    "khate": "account",
    "paisa": "money",
    "paise": "money",
    "rupaye": "rupees",
    "rupya": "rupees",
    "jama": "credited",
    "nikale": "withdrawn",
    "kat": "debited",
    "kate": "debited",
    "bhugtan": "payment",
    "udhar": "loan",
    "tankhwah": "salary",
    "pagar": "salary",
    "dawa": "medicine",
    "dawai": "medicine",
    "aspataal": "hospital",
    "khana": "food",
    "kirana": "grocery",
    "bijli": "electricity",
    "pani": "water",
    "gaadi": "transport",
    "auto": "transport",
    "petrol": "fuel",
    "fees": "education",
    "kitab": "education",
}

# Native Script Financial Keyword Translations (for cross-lingual semantic alignment)
INDIC_FINANCIAL_GLOSSARY = {
    # Hindi
    "खाता": "account",
    "खाते": "account",
    "डेबिट": "debited",
    "क्रेडिट": "credited",
    "दिनांक": "date",
    "संदर्भ": "reference",
    "शेष": "balance",
    "भुगतान": "payment",
    "वेतन": "salary",
    # Telugu
    "ఖాతా": "account",
    "నుండి": "from",
    "డెబిట్": "debited",
    "క్రెడిట్": "credited",
    "తేదీ": "date",
    "బ్యాలెన్స్": "balance",
    # Tamil
    "கணக்கு": "account",
    "டெபிட்": "debited",
    "கிரெடிட்": "credited",
    "தேதி": "date",
    "இருப்பு": "balance",
    # Bengali
    "অ্যাকাউন্ট": "account",
    "ডেবিট": "debited",
    "ক্রেডিট": "credited",
    "তারিখ": "date",
    "ব্যালেন্স": "balance",
    # Kannada
    "ಖಾತೆ": "account",
    "ಖಾತೆಯಿಂದ": "from account",
    "ಡೆಬಿಟ್": "debited",
    "ಕ್ರೆడిಟ್": "credited",
    "ದಿನಾಂಕ": "date",
    "ಬ್ಯಾಲೆನ್ಸ್": "balance",
}

# Prompt prefixes present in FinEE instruction user messages
PROMPT_PREFIX_REGEX = re.compile(
    r"^(?:Extract the financial entities from the following message:|"
    r"Extract structured data from this bank notification:|"
    r"Identify transaction details in this message:|"
    r"Analyze this transaction message and extract details:|"
    r"Identify and extract all transaction details:|"
    r"Parse this banking SMS and extract entities:|"
    r"Extract financial entities from:)\s*",
    re.IGNORECASE,
)


def strip_instruction_prompt(text: str) -> str:
    """Removes ChatML instruction wrapper prompt if present to isolate raw SMS text."""
    if not text:
        return ""
    cleaned = PROMPT_PREFIX_REGEX.sub("", text.strip())
    return cleaned.strip()


def detect_language_and_codemixing(text: str) -> Tuple[str, bool, Dict[str, float]]:
    """
    Detects the primary language ('en', 'hi', 'ta', 'te', 'bn', 'kn', or 'hinglish')
    and determines whether the message is code-mixed (combines Latin & Indic scripts
    or Romanized Indian words with English banking terms).
    """
    clean_text = strip_instruction_prompt(text)
    script_counts = {lang: 0 for lang in SCRIPT_RANGES}
    latin_count = 0

    for ch in clean_text:
        cp = ord(ch)
        if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            latin_count += 1
        else:
            for lang, (low, high) in SCRIPT_RANGES.items():
                if low <= cp <= high:
                    script_counts[lang] += 1
                    break

    total_alpha = latin_count + sum(script_counts.values())
    if total_alpha == 0:
        return "en", False, {"en": 1.0}

    # Check if any Indic script is present
    top_indic_lang, top_indic_count = max(script_counts.items(), key=lambda x: x[1])
    if top_indic_count > 0:
        # Indic script is used. Since Indian banking SMS almost always include Latin tokens
        # (like Rs., XX1234, HDFC, VPA), if both Indic and Latin are substantial, mark code-mixed.
        is_code_mixed = (latin_count / total_alpha) >= 0.15 and (top_indic_count / total_alpha) >= 0.10
        proportions = {
            top_indic_lang: round(top_indic_count / total_alpha, 3),
            "en": round(latin_count / total_alpha, 3),
        }
        return top_indic_lang, is_code_mixed, proportions

    # Pure Latin script: check for Romanized code-mixing (Hinglish / Tanglish / Kanglish)
    tokens = re.findall(r"[a-zA-Z]+", clean_text.lower())
    codemix_hits = [t for t in tokens if t in CODE_MIXED_LEXICON]
    # Require at least 2 code-mixed tokens (or 1 distinct non-ambiguous token like 'hua', 'mein', 'gaya', 'khata')
    strong_hinglish = {"mein", "hua", "hui", "gaya", "gaye", "aaya", "aaye", "khata", "khate", "rupaye", "bhugtan", "jama"}
    if any(t in strong_hinglish for t in tokens) or len(codemix_hits) >= 2:
        hi_ratio = round(len(codemix_hits) / max(len(tokens), 1), 3)
        return "hinglish", True, {"hinglish": hi_ratio, "en": round(1.0 - hi_ratio, 3)}

    return "en", False, {"en": 1.0}


def normalize_financial_text(text: str, expand_multilingual: bool = True) -> str:
    """
    Normalizes a raw financial SMS/notification for downstream NLP classification:
    - Strips instruction prefix
    - Normalizes currency symbols (₹, INR, Rs.) ->RS_TOKEN
    - Normalizes masked account numbers -> ACCT_TOKEN
    - Expands Indic & Romanized Hinglish financial terms with English semantic equivalents
      so both Classical ML and Multilingual Transformers benefit from shared features.
    """
    raw = strip_instruction_prompt(text)

    # Normalize currency symbols to standard 'Rs. '
    norm = re.sub(r"(?:₹|INR|Rs\.?|रु\.?|రూ\.?|ரூ\.?|৳|ರೂ\.?)\s*", "Rs. ", raw, flags=re.IGNORECASE)

    # Add semantic glosses for native Indic tokens and Hinglish tokens if enabled
    if expand_multilingual:
        aug_tokens = []
        for word in norm.split():
            clean_w = word.strip(".,;:!()[]{}\"'।|").lower()
            aug_tokens.append(word)
            if clean_w in INDIC_FINANCIAL_GLOSSARY:
                aug_tokens.append(INDIC_FINANCIAL_GLOSSARY[clean_w])
            elif clean_w in CODE_MIXED_LEXICON:
                aug_tokens.append(CODE_MIXED_LEXICON[clean_w])
        norm = " ".join(aug_tokens)

    # Normalize whitespace
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def preprocess_record(text: str) -> Dict[str, Any]:
    """Full preprocessing pipeline returning raw, cleaned, normalized text and language metadata."""
    raw_sms = strip_instruction_prompt(text)
    lang, is_code_mixed, lang_scores = detect_language_and_codemixing(raw_sms)
    normalized = normalize_financial_text(raw_sms, expand_multilingual=True)
    return {
        "raw_sms": raw_sms,
        "normalized_text": normalized,
        "language": lang,
        "is_code_mixed": is_code_mixed,
        "language_Confidence": lang_scores,
    }
