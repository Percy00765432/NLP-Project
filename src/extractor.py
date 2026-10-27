"""
Hybrid Financial Entity Extractor (Rule-based Pattern Recognition + Contextual NER).

Extracts all 14 FinEE structured financial fields from English, Indian-language
(Hindi, Tamil, Telugu, Bengali, Kannada), and Code-Mixed (Hinglish/Tanglish/Kanglish)
banking and UPI transaction messages:
- amount (float)
- type ("debit" | "credit")
- account (last 3-4 digits of account/card)
- bank (canonical bank name)
- date (transaction date)
- time (transaction time if present)
- reference (12-digit UPI/NEFT/IMPS reference number)
- vpa (UPI Virtual Payment Address)
- merchant (business/brand name for P2M transactions)
- beneficiary (person name for P2P transfers)
- payment_mode (UPI, IMPS, NEFT, RTGS, Credit Card, Debit Card, EMI, Wallet)
- balance (available balance / credit limit after transaction)
- is_p2m (boolean: True for merchant, False for P2P/self)
- entity_spans (character offsets & BIO labels for UI highlighting)
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from src.config import INDIAN_BANKS, MERCHANT_LEXICON, DEBIT_KEYWORDS, CREDIT_KEYWORDS
from src.preprocessor import strip_instruction_prompt, detect_language_and_codemixing


# Extended brand/merchant dictionary from FinEE dataset + Indian banking ecosystem
EXTENDED_MERCHANTS: Dict[str, Tuple[str, str]] = {
    **MERCHANT_LEXICON,
    "icici direct": ("ICICI Direct", "investment"),
    "icicidirect": ("ICICI Direct", "investment"),
    "dhan": ("Dhan", "investment"),
    "paytm money": ("Paytm Money", "investment"),
    "paytmmoney": ("Paytm Money", "investment"),
    "cesc": ("CESC", "bills"),
    "bajaj finance": ("Bajaj Finance", "emi"),
    "hdfc ergo": ("HDFC ERGO", "bills"),
    "star health": ("Star Health", "healthcare"),
    "medanta": ("Medanta", "healthcare"),
    "swiggy instamart": ("Instamart", "grocery"),
    "google pay": ("Google Pay", "transfer"),
    "phonepe": ("PhonePe", "shopping"),
    "paytm": ("Paytm", "shopping"),
    "bharatpe": ("BharatPe", "shopping"),
    "cred": ("CRED", "bills"),
}

# Regex Patterns for Indian Banking & UPI Messages
AMOUNT_PATTERNS = [
    # Standard Rs. / INR / ₹ before number (e.g., Rs.2,500.00, INR 13545, ₹ 500)
    re.compile(
        r"(?:Rs\.?|INR|₹|रु\.?|రూ\.?|ரூ\.?|৳|ರೂ\.?)\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    ),
    # Number followed by rupees / rupaye / rs (common in Hinglish: "500 rupaye", "500 rs", "500 credit hua")
    re.compile(
        r"\b([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*(?:rs\.?|inr|rupees|rupaye|टका|ரூபாய்|రూపాయలు|ರೂಪಾಯಿ)\b",
        re.IGNORECASE,
    ),
    # Code-mixed pattern: "mein 500 credit/debit hua"
    re.compile(
        r"\b(?:mein|me|for|with|of)\s+([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]{2,7}(?:\.[0-9]{1,2})?)\s+(?:credit|debit|credited|debited|kat|jama)",
        re.IGNORECASE,
    ),
]

BALANCE_PATTERNS = [
    re.compile(
        r"(?:Bal(?:ance)?|Avl\s*(?:Bal|Limit|lmt)|शेष\s*राशि|బ్యాలెన్స్|இருப்பு|ব্যালেন্স|ಬ್ಯಾಲೆನ್ಸ್)[\s:=-]*(?:Rs\.?|INR|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    ),
]

ACCOUNT_PATTERNS = [
    # Matches XX1234, XXXXX1234, *1234, ending 1909, A/c 6567, khata XX4248
    re.compile(
        r"(?:A/c|Acct|Account|Card|CC|Loan(?:\s+A/c)?|खाता|खाते|ఖాతా|கணக்கு|অ্যাকাউন্ট|ಖಾತೆ|ending)\s*(?:no\.?|number)?\s*(?:[xX\*]+)?([0-9]{3,4})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b[xX\*]{2,6}([0-9]{3,4})\b"),
]

DATE_PATTERNS = [
    # DD-MM-YYYY, DD/MM/YYYY, DD-MM-YY, DD/MM/YY
    re.compile(r"\b([0-3][0-9][-/.][0-1][0-9][-/.](?:20)?[2-9][0-9])\b"),
    # DD-MMM-YYYY or DD-MMM-YY (e.g., 16-Sep-25, 30-Oct-2025)
    re.compile(
        r"\b([0-3]?[0-9][-\s/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s/](?:20)?[2-9][0-9])\b",
        re.IGNORECASE,
    ),
    # YYYY-MM-DD
    re.compile(r"\b(20[2-9][0-9]-[0-1][0-9]-[0-3][0-9])\b"),
]

TIME_PATTERN = re.compile(r"\b([0-2][0-9]:[0-5][0-9](?::[0-5][0-9])?(?:\s*[AP]M)?)\b", re.IGNORECASE)

REFERENCE_PATTERNS = [
    # Explicit Ref / UPI Ref / IMPS Ref / संदर्भ
    re.compile(
        r"(?:UPI\s*Ref|IMPS\s*Ref|NEFT\s*Ref|Ref(?:\s*No)?|UPI|संदर्भ|రిఫరెన్స్|குறிப்பு)[\s:.-]*([0-9]{9,14})\b",
        re.IGNORECASE,
    ),
    # Standalone 12-digit UPI reference number
    re.compile(r"\b([0-9]{12})\b"),
]

VPA_PATTERN = re.compile(r"\b([a-zA-Z0-9._-]+@[a-zA-Z]{2,15})\b")

# Contextual patterns to extract Beneficiary (P2P) or Merchant (P2M) names
MERCHANT_OR_BENEFICIARY_PATTERNS = [
    # "at BookMyShow on", "at Ajio on"
    re.compile(r"\bat\s+([A-Z][A-Za-z0-9\s.&'-]{1,25}?)\s+(?:on|for|via|ref|avl)\b"),
    # "; JioCinema credited." or "; Lilu Prasad credited."
    re.compile(r";\s*([A-Z][A-Za-z0-9\s.&'-]{1,28}?)\s+credited\b"),
    # "IMPS to Amit Kumar." or "NEFT from Neha Gupta." or "from Ashok Tiwari."
    re.compile(
        r"\b(?:IMPS\s+to|NEFT\s+to|NEFT\s+from|IMPS\s+from|RTGS\s+to|UPI\s+to|UPI\s+from|from|to)\s+([A-Z][A-Za-z0-9\s.&'-]{2,28}?)(?:[.\n;]|(?:\s+(?:on|Ref|UPI|Bal|via|VPA)))"
    ),
    # "Info: UPI-Airtel." or "UPI/zerodha@hdfcbank"
    re.compile(r"Info:\s*(?:UPI|IMPS|NEFT)[-/]([A-Za-z0-9\s.&'-]{2,25}?)(?:[.\n;]|$)"),
    # "for your Swiggy payment" or "for Instamart payment"
    re.compile(r"\bfor\s+(?:your\s+)?([A-Z][A-Za-z0-9\s.&'-]{2,20}?)\s+payment\b"),
]


class FinancialEntityExtractor:
    """
    Hybrid Rule-Based + Contextual Named Entity Recognition (NER) Extractor
    for Multilingual & Code-Mixed Indian Financial Messages.
    """

    def __init__(self) -> None:
        self.banks = INDIAN_BANKS
        self.merchants = EXTENDED_MERCHANTS

    def extract_amount_and_balance(
        self, text: str
    ) -> Tuple[Optional[float], Optional[float], Optional[Tuple[int, int]]]:
        """Extracts primary transaction amount and optional post-transaction balance."""
        balance = None
        bal_span = None
        for pat in BALANCE_PATTERNS:
            m = pat.search(text)
            if m:
                try:
                    balance = float(m.group(1).replace(",", ""))
                    bal_span = m.span(0)
                    break
                except ValueError:
                    pass

        amount = None
        amt_span = None
        for pat in AMOUNT_PATTERNS:
            for m in pat.finditer(text):
                # Skip if this match is inside the balance span
                if bal_span and m.start() >= bal_span[0] and m.end() <= bal_span[1]:
                    continue
                try:
                    val = float(m.group(1).replace(",", ""))
                    amount = val
                    amt_span = m.span(0)
                    break
                except ValueError:
                    continue
            if amount is not None:
                break

        return amount, balance, amt_span

    def extract_transaction_type(self, text: str) -> str:
        """Determines whether a transaction is 'debit' or 'credit' across 6 languages + Hinglish."""
        lower_text = text.lower()

        # Special case: ICICI style "Acct XX6291 debited for Rs 150.00 ...; JioCinema credited."
        # Here the user's account is debited first.
        debit_pos = 999999
        credit_pos = 999999

        for kw in DEBIT_KEYWORDS:
            idx = lower_text.find(kw)
            if idx != -1 and idx < debit_pos:
                debit_pos = idx

        for kw in CREDIT_KEYWORDS:
            idx = lower_text.find(kw)
            if idx != -1 and idx < credit_pos:
                credit_pos = idx

        if debit_pos == 999999 and credit_pos == 999999:
            return "debit"  # Default for expense alerts
        return "debit" if debit_pos <= credit_pos else "credit"

    def extract_bank(self, text: str) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
        """Identifies the bank issuing the message across English and Indic scripts."""
        lower_text = text.lower()
        best_bank = None
        best_pos = 999999
        best_span = None

        for canonical_bank, aliases in self.banks.items():
            for alias in aliases:
                # Word boundary check for Latin aliases
                if alias.isascii():
                    m = re.search(rf"\b{re.escape(alias)}\b", lower_text)
                    if m and m.start() < best_pos:
                        best_pos = m.start()
                        best_bank = canonical_bank
                        best_span = m.span(0)
                else:
                    idx = lower_text.find(alias)
                    if idx != -1 and idx < best_pos:
                        best_pos = idx
                        best_bank = canonical_bank
                        best_span = (idx, idx + len(alias))

        return best_bank, best_span

    def extract_account(self, text: str) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
        """Extracts the last 3-4 digits of the bank account or card."""
        for pat in ACCOUNT_PATTERNS:
            m = pat.search(text)
            if m:
                return m.group(1), m.span(0)
        return None, None

    def extract_date_and_time(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], Optional[Tuple[int, int]]]:
        """Extracts transaction date and optional timestamp."""
        date_str = None
        date_span = None
        for pat in DATE_PATTERNS:
            m = pat.search(text)
            if m:
                date_str = m.group(1)
                date_span = m.span(1)
                break

        time_str = None
        tm = TIME_PATTERN.search(text)
        if tm:
            time_str = tm.group(1)

        return date_str, time_str, date_span

    def extract_vpa_and_reference(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Extracts UPI VPA handle and 12-digit transaction reference ID."""
        vpa = None
        vpa_span = None
        vm = VPA_PATTERN.search(text)
        if vm:
            vpa = vm.group(1)
            vpa_span = vm.span(1)

        ref = None
        ref_span = None
        for pat in REFERENCE_PATTERNS:
            rm = pat.search(text)
            if rm:
                candidate = rm.group(1)
                # Avoid matching customer care numbers like 18002586161
                if not candidate.startswith("1800"):
                    ref = candidate
                    ref_span = rm.span(1)
                    break

        return vpa, ref, vpa_span, ref_span

    def extract_payment_mode(self, text: str, vpa: Optional[str]) -> str:
        """Detects the payment channel/instrument (UPI, Credit Card, NEFT, IMPS, EMI, etc.)."""
        lower = text.lower()
        if "upi" in lower or vpa is not None:
            return "UPI"
        if "credit card" in lower or " cc " in lower or "amex card" in lower or "card ending" in lower:
            return "Credit Card"
        if "debit card" in lower or "atm" in lower or "pos " in lower:
            return "Debit Card"
        if "imps" in lower:
            return "IMPS"
        if "neft" in lower:
            return "NEFT"
        if "rtgs" in lower:
            return "RTGS"
        if "emi" in lower or "loan" in lower or "auto-debit" in lower:
            return "EMI / Auto-Debit"
        if "wallet" in lower or "cashback" in lower or "reward" in lower:
            return "Wallet / Cashback"
        return "Bank Transfer"

    def extract_merchant_or_beneficiary(
        self, text: str, vpa: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], bool, Optional[Tuple[int, int]]]:
        """
        Resolves Merchant (P2M) or Beneficiary (P2P) using:
        1. VPA prefix lookup (e.g., netmeds@icici -> Netmeds, priya13@apl -> Priya)
        2. Lexicon match in message body
        3. Contextual NER span patterns ("at <Entity> on", "IMPS to <Entity>", "; <Entity> credited")
        Returns: (merchant, beneficiary, lexicon_category, is_p2m, span)
        """
        lower_text = text.lower()

        # 1. Check VPA prefix against known merchants first
        if vpa:
            vpa_prefix = vpa.split("@")[0].lower()
            vpa_clean = re.sub(r"[0-9_.-]+$", "", vpa_prefix)
            for key, (canon_name, cat) in self.merchants.items():
                key_compact = key.strip().replace(" ", "")
                if vpa_clean == key_compact or key_compact in vpa_clean:
                    idx = lower_text.find(vpa.lower())
                    span = (idx, idx + len(vpa)) if idx != -1 else None
                    return canon_name, None, cat, True, span

        # 2. Check contextual patterns in text for explicit Merchant or Person names
        extracted_candidate = None
        candidate_span = None
        for pat in MERCHANT_OR_BENEFICIARY_PATTERNS:
            m = pat.search(text)
            if m:
                cand = m.group(1).strip(" .-;:")
                # Filter out bank names or generic words
                if cand.lower() not in {"a/c", "acct", "account", "your", "bank", "upi", "imps", "neft"}:
                    extracted_candidate = cand
                    candidate_span = m.span(1)
                    break

        # 3. Check if extracted_candidate or text matches our known merchant lexicon
        for key, (canon_name, cat) in sorted(self.merchants.items(), key=lambda x: -len(x[0])):
            if key in {"phonepe", "paytm", "google pay"} and extracted_candidate:
                continue  # Prefer specific merchant over payment app if both appear
            if key.strip() in lower_text:
                # Ensure word boundary for short keys
                m = re.search(rf"\b{re.escape(key.strip())}\b", lower_text)
                if m:
                    return canon_name, None, cat, True, m.span(0)

        # 4. If we found a contextual candidate not in our static dictionary, classify as P2M vs P2P
        if extracted_candidate:
            business_indicators = {
                "hotel", "mart", "store", "pharmacy", "hospital", "clinic", "travels",
                "airlines", "power", "gas", "electric", "direct", "finance", "capital",
                "ltd", "pvt", "enterprise", "RESTAURANT", "cafe", "university", "college",
                "school", "academy", "cinema", "club", "fit",
            }
            cand_lower = extracted_candidate.lower()
            if any(ind in cand_lower for ind in business_indicators) or len(extracted_candidate.split()) == 1:
                return extracted_candidate, None, None, True, candidate_span
            else:
                # Likely a person name (e.g., "Amit Kumar", "Neha Gupta", "Lilu Prasad")
                return None, extracted_candidate, "transfer", False, candidate_span

        # 5. If VPA looks like a person handle (e.g. rahul12@okaxis, kiran5@okhdfcbank)
        if vpa:
            vpa_user = vpa.split("@")[0]
            person_prefix = re.sub(r"[0-9._-]+$", "", vpa_user)
            if person_prefix and len(person_prefix) >= 3:
                idx = lower_text.find(vpa.lower())
                span = (idx, idx + len(vpa)) if idx != -1 else None
                return None, person_prefix.capitalize(), "transfer", False, span

        return None, None, None, False, None

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Runs the complete extraction pipeline on a financial message and returns structured
        entities along with character spans for visual NER highlighting.
        """
        raw_sms = strip_instruction_prompt(text)
        lang, is_code_mixed, lang_conf = detect_language_and_codemixing(raw_sms)

        amount, balance, amt_span = self.extract_amount_and_balance(raw_sms)
        txn_type = self.extract_transaction_type(raw_sms)
        bank, bank_span = self.extract_bank(raw_sms)
        account, acct_span = self.extract_account(raw_sms)
        date_str, time_str, date_span = self.extract_date_and_time(raw_sms)
        vpa, reference, vpa_span, ref_span = self.extract_vpa_and_reference(raw_sms)
        payment_mode = self.extract_payment_mode(raw_sms, vpa)
        merchant, beneficiary, lexicon_category, is_p2m, party_span = (
            self.extract_merchant_or_beneficiary(raw_sms, vpa)
        )

        # Build NER span annotations for UI & token-level inspection
        spans: List[Dict[str, Any]] = []
        if bank and bank_span:
            spans.append({"label": "BANK", "text": raw_sms[bank_span[0]:bank_span[1]], "start": bank_span[0], "end": bank_span[1], "value": bank})
        if account and acct_span:
            spans.append({"label": "ACCOUNT", "text": raw_sms[acct_span[0]:acct_span[1]], "start": acct_span[0], "end": acct_span[1], "value": account})
        if amount is not None and amt_span:
            spans.append({"label": "AMOUNT", "text": raw_sms[amt_span[0]:amt_span[1]], "start": amt_span[0], "end": amt_span[1], "value": amount})
        if date_str and date_span:
            spans.append({"label": "DATE", "text": raw_sms[date_span[0]:date_span[1]], "start": date_span[0], "end": date_span[1], "value": date_str})
        if merchant and party_span:
            spans.append({"label": "MERCHANT", "text": raw_sms[party_span[0]:party_span[1]], "start": party_span[0], "end": party_span[1], "value": merchant})
        elif beneficiary and party_span:
            spans.append({"label": "BENEFICIARY", "text": raw_sms[party_span[0]:party_span[1]], "start": party_span[0], "end": party_span[1], "value": beneficiary})
        if vpa and vpa_span:
            spans.append({"label": "VPA", "text": raw_sms[vpa_span[0]:vpa_span[1]], "start": vpa_span[0], "end": vpa_span[1], "value": vpa})
        if reference and ref_span:
            spans.append({"label": "REFERENCE", "text": raw_sms[ref_span[0]:ref_span[1]], "start": ref_span[0], "end": ref_span[1], "value": reference})

        spans.sort(key=lambda s: s["start"])

        return {
            "raw_sms": raw_sms,
            "amount": amount,
            "type": txn_type,
            "bank": bank,
            "account": account,
            "date": date_str,
            "time": time_str,
            "reference": reference,
            "vpa": vpa,
            "merchant": merchant,
            "beneficiary": beneficiary,
            "payment_mode": payment_mode,
            "balance": balance,
            "is_p2m": is_p2m,
            "lexicon_category_hint": lexicon_category,
            "language": lang,
            "is_code_mixed": is_code_mixed,
            "language_confidence": lang_conf,
            "entity_spans": spans,
        }
