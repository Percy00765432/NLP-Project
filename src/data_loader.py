"""
FinEE Dataset Loader & Stratified Code-Mixed/Education Augmentation Pipeline.

Supports:
1. Streaming or downloading from `Ranjit0034/finee-dataset` on Hugging Face
2. Parsing ChatML `messages` format (system, user, assistant JSON) into flat tabular records
3. Stratifying across all 6 FinEE languages (en, hi, ta, te, bn, kn) and categories
4. Augmenting with realistic Indian Code-Mixed (Hinglish, Tanglish, Kanglish) and
   Education-category financial messages (from Project Synopsis Objective #2 & #3)
5. Saving clean train/valid/test splits to `data/` as CSV and JSONL for fast reproducible runs.
"""

import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.config import DATA_DIR, HF_DATASET_ID, SYNOPSIS_CATEGORY_MAP
from src.preprocessor import strip_instruction_prompt, detect_language_and_codemixing, normalize_financial_text


# Realistic Code-Mixed (Hinglish, Tanglish, Kanglish) & Education SMS templates
# to ensure strong representation of Synopsis Objective #2 (Education) and Objective #3 (Code-mixing)
AUGMENTED_TEMPLATES: List[Dict[str, Any]] = [
    # Hinglish Code-Mixed (Hindi + English in Latin script)
    {
        "template": "{bank} Bank Alert: Aapke A/c XX{acct} se Rs.{amt} debit hua on {date} to {vpa}. UPI Ref: {ref}.",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "debit",
    },
    {
        "template": "Dear Customer, aapke {bank} khate XX{acct} mein Rs.{amt} credit hua on {date} from {vpa}. Ref {ref}.",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "credit",
    },
    {
        "template": "{bank}: A/c XX{acct} se INR {amt} kat gaya for {merchant} payment on {date}. UPI Ref:{ref}. Avl Bal Rs.{bal}",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "debit",
    },
    {
        "template": "Aapke {bank} Credit Card XX{acct} par Rs.{amt} ka bhugtan {merchant} par सफल raha on {date}. Ref: {ref}",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "debit",
    },
    # Kanglish / Kannada Code-Mixed
    {
        "template": "{bank} Alert: Nimma A/c XX{acct} inda Rs.{amt} {merchant} ge UPI mulaka debit agide on {date}. Ref: {ref}",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "debit",
    },
    # Tanglish / Tamil Code-Mixed
    {
        "template": "{bank} Bank: Unga A/c XX{acct} la irundhu Rs.{amt} {merchant} ku debit aagiduchu on {date}. UPI Ref: {ref}",
        "lang": "hinglish",
        "is_code_mixed": True,
        "type": "debit",
    },
]

MERCHANT_SCENARIOS = [
    # Food
    ("Swiggy", "swiggy@ybl", "food", (120, 1200)),
    ("Zomato", "zomato@hdfcbank", "food", (150, 1500)),
    ("Domino's", "dominos@icici", "food", (250, 1100)),
    ("Starbucks", "starbucks@axis", "food", (280, 950)),
    # Grocery
    ("Zepto", "zepto@ybl", "grocery", (180, 2200)),
    ("BigBasket", "bigbasket@icici", "grocery", (400, 3500)),
    ("Blinkit", "blinkit@paytm", "grocery", (150, 1800)),
    ("DMart", "dmart@hdfcbank", "grocery", (600, 4800)),
    # Shopping
    ("Amazon", "amazon@apl", "shopping", (299, 15000)),
    ("Flipkart", "flipkart@ybl", "shopping", (350, 18000)),
    ("Myntra", "myntra@ybl", "shopping", (499, 6500)),
    ("Meesho", "meesho@paytm", "shopping", (199, 2500)),
    ("Nykaa", "nykaa@icici", "shopping", (350, 4200)),
    # Transport & Travel
    ("Uber", "uber@axis", "transport", (85, 850)),
    ("Ola", "ola@icici", "transport", (75, 780)),
    ("Rapido", "rapido@ybl", "transport", (45, 320)),
    ("IRCTC", "irctc@sbi", "travel", (450, 4500)),
    ("MakeMyTrip", "makemytrip@hdfcbank", "travel", (2200, 18500)),
    ("IndiGo Airlines", "indigo@icici", "travel", (3500, 14000)),
    # Bills
    ("Airtel", "airtel@axis", "bills", (199, 1499)),
    ("Jio", "jio@paytm", "bills", (239, 2999)),
    ("BESCOM Electricity", "bescom@ybl", "bills", (550, 4200)),
    ("Tata Power", "tatapower@icici", "bills", (800, 5100)),
    ("ACT Fibernet", "actfibernet@hdfcbank", "bills", (799, 1999)),
    # Healthcare
    ("Apollo Pharmacy", "apollo@hdfcbank", "healthcare", (180, 3200)),
    ("PharmEasy", "pharmeasy@icici", "healthcare", (250, 2800)),
    ("Netmeds", "netmeds@icici", "healthcare", (300, 3500)),
    ("Practo", "practo@paytm", "healthcare", (400, 1500)),
    ("Manipal Hospital", "manipal@axis", "healthcare", (850, 15000)),
    # Education (Explicitly required by Project Synopsis Objective #2)
    ("Udemy", "udemy@ybl", "education", (399, 3499)),
    ("Coursera", "coursera@hdfcbank", "education", (1200, 4999)),
    ("Unacademy", "unacademy@icici", "education", (1500, 18000)),
    ("BYJU'S", "byjus@axis", "education", (2500, 25000)),
    ("PhysicsWallah", "pw@ybl", "education", (999, 6500)),
    ("RV University", "rvuniversity@sbi", "education", (15000, 95000)),
    ("Scaler Academy", "scaler@hdfcbank", "education", (5000, 45000)),
    # Entertainment
    ("Netflix", "netflix@axis", "entertainment", (199, 649)),
    ("BookMyShow", "bookmyshow@ybl", "entertainment", (250, 1600)),
    ("JioCinema", "jiocinema@icici", "entertainment", (29, 999)),
    ("Spotify", "spotify@hdfcbank", "entertainment", (119, 599)),
    # Investment
    ("Zerodha", "zerodha@hdfcbank", "investment", (2000, 50000)),
    ("Groww", "groww@icici", "investment", (1000, 35000)),
    ("Upstox", "upstox@icici", "investment", (1500, 40000)),
]

EDUCATION_ENGLISH_AND_INDIC_TEMPLATES = [
    ("HDFC Bank: Rs.{amt} debited from A/c XX{acct} on {date}. VPA {vpa}. Info: {merchant} Course Fee. UPI Ref: {ref}", "en", False),
    ("SBI: INR {amt} paid from A/c XX{acct} on {date} towards {merchant} Tuition Fee. Ref: {ref}. Avl Bal: Rs.{bal}", "en", False),
    ("ICICI Bank Acct XX{acct} debited for Rs {amt} on {date}; {merchant} credited. UPI:{ref}.", "en", False),
    ("Axis Bank: Rs.{amt} spent on Credit Card XX{acct} at {merchant} on {date} for Online Certification.", "en", False),
    ("HDFC: आपके खाते XX{acct} से Rs.{amt} डेबिट हुआ। दिनांक {date}। {vpa} ({merchant} शिक्षण शुल्क)। संदर्भ: {ref}", "hi", True),
    ("SBI: ನಿಮ್ಮ ಖಾತೆ XX{acct} ನಿಂದ Rs.{amt} ಡೆಬಿಟ್ ಆಗಿದೆ. ದಿನಾಂಕ {date}. {vpa} ({merchant}). Ref: {ref}", "kn", True),
    ("ICICI: మీ ఖాతా XX{acct} నుండి Rs.{amt} డెబిట్ చేయబడింది. తేదీ {date}. {vpa} ({merchant}). Ref: {ref}", "te", True),
    ("Kotak: உங்கள் கணக்கு XX{acct} இல் இருந்து Rs.{amt} டெபிட் செய்யப்பட்டது. தேதி {date}. {vpa} ({merchant}). Ref: {ref}", "ta", True),
    ("Axis: আপনার অ্যাকাউন্ট XX{acct} থেকে Rs.{amt} ডেবিট হয়েছে। তারিখ {date}। {vpa} ({merchant})। Ref: {ref}", "bn", True),
]


def parse_finee_row(row_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses a single row from Ranjit0034/finee-dataset (either ChatML `messages` list
    or direct `input`/`output` dict) into a standardized dictionary.
    """
    raw_input = ""
    output_dict = {}

    if "messages" in row_obj and isinstance(row_obj["messages"], list):
        for msg in row_obj["messages"]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                raw_input = strip_instruction_prompt(content)
            elif role == "assistant":
                try:
                    output_dict = json.loads(content)
                except Exception:
                    return None
    elif "input" in row_obj and "output" in row_obj:
        raw_input = strip_instruction_prompt(str(row_obj["input"]))
        out_val = row_obj["output"]
        if isinstance(out_val, str):
            try:
                output_dict = json.loads(out_val)
            except Exception:
                return None
        elif isinstance(out_val, dict):
            output_dict = out_val

    if not raw_input or not output_dict:
        return None

    # Normalize category
    category = str(output_dict.get("category", "")).strip().lower()
    if category in {"cashback", "refund"}:
        category = "shopping"
    if not category:
        # Infer from merchant if missing
        merch_lower = str(output_dict.get("merchant", "")).lower()
        if any(k in merch_lower for k in ["swiggy", "zomato", "hotel", "domino", "kfc"]):
            category = "food"
        elif any(k in merch_lower for k in ["amazon", "flipkart", "myntra", "meesho", "ajio"]):
            category = "shopping"
        elif any(k in merch_lower for k in ["uber", "ola", "rapido"]):
            category = "transport"
        else:
            category = "shopping"

    lang_detected, is_cm, _ = detect_language_and_codemixing(raw_input)
    lang = output_dict.get("language", lang_detected)
    if lang_detected == "hinglish":
        lang = "hinglish"

    norm_text = normalize_financial_text(raw_input, expand_multilingual=True)

    return {
        "raw_sms": raw_input,
        "normalized_text": norm_text,
        "amount": float(output_dict["amount"]) if output_dict.get("amount") is not None else None,
        "type": output_dict.get("type", "debit"),
        "bank": output_dict.get("bank"),
        "account": output_dict.get("account"),
        "date": output_dict.get("date"),
        "reference": output_dict.get("reference"),
        "merchant": output_dict.get("merchant"),
        "beneficiary": output_dict.get("beneficiary"),
        "vpa": output_dict.get("vpa"),
        "category": category,
        "synopsis_category": SYNOPSIS_CATEGORY_MAP.get(category, "Shopping"),
        "is_p2m": bool(output_dict.get("is_p2m", output_dict.get("merchant") is not None)),
        "language": lang,
        "is_code_mixed": is_cm,
        "source": "finee_hf",
    }


def generate_augmented_samples(n_codemixed: int = 1200, n_education: int = 800, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generates realistic Indian Code-Mixed (Hinglish/Tanglish/Kanglish) and Education
    financial messages to complement the FinEE dataset so all Project Synopsis objectives
    are thoroughly represented.
    """
    rng = random.Random(seed)
    banks = ["HDFC", "SBI", "ICICI", "Axis", "Kotak", "PNB", "BOB", "YES Bank", "IndusInd"]
    records: List[Dict[str, Any]] = []

    # 1. Generate Code-Mixed messages across all categories
    for _ in range(n_codemixed):
        tpl_info = rng.choice(AUGMENTED_TEMPLATES)
        bank = rng.choice(banks)
        acct = f"{rng.randint(1000, 9999)}"
        date = f"{rng.randint(1, 28):02d}-{rng.randint(1, 12):02d}-2025"
        ref = f"{rng.randint(100000000000, 999999999999)}"
        bal = f"{rng.randint(2500, 185000):,}"

        if tpl_info["type"] == "credit":
            person = rng.choice(["Rahul Sharma", "Priya Nair", "Amit Verma", "Sneha Reddy", "Karthik Rao", "Ananya Das"])
            vpa = f"{person.split()[0].lower()}{rng.randint(10,99)}@okaxis"
            amt = round(rng.uniform(500, 45000), 2)
            cat = rng.choice(["transfer", "salary"])
            if cat == "salary":
                vpa = "infosys.payroll@hdfcbank"
                amt = float(rng.randint(35000, 125000))
            sms = tpl_info["template"].format(
                bank=bank, acct=acct, amt=f"{amt:,.2f}", date=date, vpa=vpa, merchant=person, ref=ref, bal=bal
            )
            merchant_val = "Infosys Payroll" if cat == "salary" else None
            benef_val = None if cat == "salary" else person
            is_p2m = cat == "salary"
        else:
            merch, vpa, cat, (low_a, high_a) = rng.choice(MERCHANT_SCENARIOS)
            amt = round(rng.uniform(low_a, high_a), 2)
            sms = tpl_info["template"].format(
                bank=bank, acct=acct, amt=f"{amt:,.2f}", date=date, vpa=vpa, merchant=merch, ref=ref, bal=bal
            )
            merchant_val = merch
            benef_val = None
            is_p2m = True

        records.append({
            "raw_sms": sms,
            "normalized_text": normalize_financial_text(sms, expand_multilingual=True),
            "amount": amt,
            "type": tpl_info["type"],
            "bank": bank,
            "account": acct,
            "date": date,
            "reference": ref,
            "merchant": merchant_val,
            "beneficiary": benef_val,
            "vpa": vpa,
            "category": cat,
            "synopsis_category": SYNOPSIS_CATEGORY_MAP.get(cat, "Shopping"),
            "is_p2m": is_p2m,
            "language": tpl_info["lang"],
            "is_code_mixed": True,
            "source": "synopsis_codemix_aug",
        })

    # 2. Generate Education category messages (English + 5 Indic scripts)
    edu_merchants = [m for m in MERCHANT_SCENARIOS if m[2] == "education"]
    for _ in range(n_education):
        tpl_str, lang, is_cm = rng.choice(EDUCATION_ENGLISH_AND_INDIC_TEMPLATES)
        merch, vpa, cat, (low_a, high_a) = rng.choice(edu_merchants)
        bank = rng.choice(banks)
        acct = f"{rng.randint(1000, 9999)}"
        date = f"{rng.randint(1, 28):02d}-{rng.randint(1, 12):02d}-2025"
        ref = f"{rng.randint(100000000000, 999999999999)}"
        bal = f"{rng.randint(5000, 150000):,}"
        amt = round(rng.uniform(low_a, high_a), 2)

        sms = tpl_str.format(
            bank=bank, acct=acct, amt=f"{amt:,.2f}", date=date, vpa=vpa, merchant=merch, ref=ref, bal=bal
        )
        records.append({
            "raw_sms": sms,
            "normalized_text": normalize_financial_text(sms, expand_multilingual=True),
            "amount": amt,
            "type": "debit",
            "bank": bank,
            "account": acct,
            "date": date,
            "reference": ref,
            "merchant": merch,
            "beneficiary": None,
            "vpa": vpa,
            "category": "education",
            "synopsis_category": SYNOPSIS_CATEGORY_MAP["education"],
            "is_p2m": True,
            "language": lang,
            "is_code_mixed": is_cm,
            "source": "synopsis_edu_aug",
        })

    return records


def load_or_build_dataset(
    max_train_samples: int = 16000,
    max_eval_samples: int = 3000,
    force_download: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads cached train/valid/test DataFrames from `data/` if available; otherwise
    streams `Ranjit0034/finee-dataset` from Hugging Face, parses all entities,
    augments with Code-Mixed & Education examples, and saves to disk.
    """
    train_path = DATA_DIR / "train_processed.parquet"
    valid_path = DATA_DIR / "valid_processed.parquet"
    test_path = DATA_DIR / "test_processed.parquet"

    if not force_download and train_path.exists() and valid_path.exists() and test_path.exists():
        return (
            pd.read_parquet(train_path),
            pd.read_parquet(valid_path),
            pd.read_parquet(test_path),
        )

    from datasets import load_dataset

    print(f"Streaming '{HF_DATASET_ID}' from Hugging Face Hub...")
    ds_stream = load_dataset(HF_DATASET_ID, streaming=True)

    def collect_split(split_name: str, limit: int) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        split_iter = ds_stream[split_name]
        for item in split_iter:
            parsed = parse_finee_row(item)
            if parsed is not None:
                rows.append(parsed)
                if len(rows) >= limit:
                    break
        return rows

    train_rows = collect_split("train", max_train_samples)
    # Check if validation split is named 'validation' or 'valid'
    val_key = "validation" if "validation" in ds_stream else "valid"
    valid_rows = collect_split(val_key, max_eval_samples)
    test_rows = collect_split("test", max_eval_samples)

    # Augment with Code-Mixed (Hinglish/Tanglish/Kanglish) & Education transactions
    aug_train = generate_augmented_samples(n_codemixed=1200, n_education=800, seed=42)
    aug_valid = generate_augmented_samples(n_codemixed=250, n_education=150, seed=101)
    aug_test = generate_augmented_samples(n_codemixed=250, n_education=150, seed=202)

    df_train = pd.DataFrame(train_rows + aug_train).sample(frac=1.0, random_state=42).reset_index(drop=True)
    df_valid = pd.DataFrame(valid_rows + aug_valid).sample(frac=1.0, random_state=42).reset_index(drop=True)
    df_test = pd.DataFrame(test_rows + aug_test).sample(frac=1.0, random_state=42).reset_index(drop=True)

    df_train.to_parquet(train_path, index=False)
    df_valid.to_parquet(valid_path, index=False)
    df_test.to_parquet(test_path, index=False)

    # Also save a readable CSV sample for easy inspection
    df_test.head(500).to_csv(DATA_DIR / "sample_test_500.csv", index=False)

    print(
        f"Saved dataset splits -> Train: {len(df_train):,}, Valid: {len(df_valid):,}, Test: {len(df_test):,}"
    )
    return df_train, df_valid, df_test
