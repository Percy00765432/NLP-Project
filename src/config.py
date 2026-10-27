"""
Configuration, constants, multilingual lexicons, and merchant dictionaries
for the Financial Transaction Extraction and Expense Categorization Framework.
"""

from pathlib import Path
from typing import Dict, List

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
OUTPUTS_DIR = ROOT_DIR / "outputs"
NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

for _dir in [DATA_DIR, MODELS_DIR, OUTPUTS_DIR, NOTEBOOKS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# Dataset configuration
HF_DATASET_ID = "Ranjit0034/finee-dataset"
DEFAULT_SUBSET_SIZE = 20000  # Fast local stratified training size (configurable up to 152,519)

# Supported Languages (from FinEE + Indian code-mixing)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "hinglish": "Code-Mixed (Hinglish / Tanglish / Kanglish)",
}

# Standard FinEE 12 Categories + Education (from Project Synopsis Objective #2)
EXPENSE_CATEGORIES = [
    "food",
    "grocery",
    "shopping",
    "transport",
    "travel",
    "bills",
    "entertainment",
    "healthcare",
    "education",
    "investment",
    "transfer",
    "salary",
    "emi",
]

# Mapping from fine-grained FinEE categories to the 6 core Synopsis categories + Income/Transfer
SYNOPSIS_CATEGORY_MAP: Dict[str, str] = {
    "food": "Food & Dining",
    "grocery": "Food & Dining",
    "shopping": "Shopping",
    "transport": "Travel & Transport",
    "travel": "Travel & Transport",
    "bills": "Bills & Utilities",
    "entertainment": "Entertainment & Lifestyle",
    "healthcare": "Healthcare",
    "education": "Education",
    "investment": "Investments & Wealth",
    "emi": "Bills & Utilities",
    "transfer": "P2P Transfers",
    "salary": "Income & Salary",
}

# Known Indian Banks
INDIAN_BANKS: Dict[str, List[str]] = {
    "HDFC": ["hdfc", "hdfcbank", "एचडीएफसी", "హెచ్‌డిఎఫ్‌సి", "எச்டிஎஃப்சி", "এইচডিএফসি", "ಎಚ್‌ಡಿಎಫ್‌ಸಿ"],
    "SBI": ["sbi", "state bank of india", "state bank", "एसबीआई", "ఎస్‌బిఐ", "எஸ்பிஐ", "এসবিআই", "ಎಸ್‌ಬಿಐ"],
    "ICICI": ["icici", "icicibank", "आईसीआईसीआई", "ఐసిఐసిఐ", "ஐசிஐசிஐ", "আইসিআইসিআই", "ಐಸಿಐಸಿಐ"],
    "Axis": ["axis", "axis bank", "axisbank", "एक्सिस", "యాక్సిస్", "ஆக்சிஸ்", "অ্যাক্সিস", "ಆಕ್ಸಿಸ್"],
    "Kotak": ["kotak", "kotak mahindra", "कोटक", "కోటక్", "கோடக்", "কোটাক", "ಕೋಟಕ್"],
    "PNB": ["pnb", "punjab national bank", "पीएनबी"],
    "BOB": ["bob", "bank of baroda", "बैंक ऑफ बड़ौदा", "baroda"],
    "Canara": ["canara", "canara bank", "केनरा", "ಕೆನರಾ"],
    "Union": ["union bank", "union", "यूनियन बैंक"],
    "IDBI": ["idbi", "idbi bank"],
    "IndusInd": ["indusind", "indusind bank"],
    "YES Bank": ["yes bank", "yesbank", "यस बैंक"],
    "Federal": ["federal", "federal bank"],
    "IDFC First": ["idfc", "idfc first"],
    "South Indian": ["south indian bank", "sib"],
    "Karur Vysya": ["karur vysya", "kvb"],
    "Amex": ["amex", "american express"],
    "Citi": ["citi", "citibank"],
    "Paytm Payments Bank": ["paytm bank", "ppbl"],
}

# Comprehensive Merchant & Brand Lexicon mapped to (Canonical Merchant Name, Category)
MERCHANT_LEXICON: Dict[str, tuple] = {
    # Food & Delivery
    "swiggy": ("Swiggy", "food"),
    "zomato": ("Zomato", "food"),
    "dominos": ("Domino's", "food"),
    "mcdonalds": ("McDonald's", "food"),
    "kfc": ("KFC", "food"),
    "starbucks": ("Starbucks", "food"),
    "burgerking": ("Burger King", "food"),
    "burger king": ("Burger King", "food"),
    "pizzahut": ("Pizza Hut", "food"),
    "pizza hut": ("Pizza Hut", "food"),
    "eatfit": ("EatFit", "food"),
    "faasos": ("Faasos", "food"),
    "haldiram": ("Haldiram's", "food"),
    "barbeque nation": ("Barbeque Nation", "food"),
    "chaayos": ("Chaayos", "food"),
    "cafe coffee day": ("Cafe Coffee Day", "food"),
    "ccd": ("Cafe Coffee Day", "food"),

    # Grocery & Quick Commerce
    "zepto": ("Zepto", "grocery"),
    "bigbasket": ("BigBasket", "grocery"),
    "blinkit": ("Blinkit", "grocery"),
    "instamart": ("Swiggy Instamart", "grocery"),
    "dmart": ("DMart", "grocery"),
    "jiomart": ("JioMart", "grocery"),
    "reliance fresh": ("Reliance Fresh", "grocery"),
    "more supermarket": ("More Supermarket", "grocery"),
    "nature basket": ("Nature's Basket", "grocery"),
    "dunzo": ("Dunzo", "grocery"),
    "country delight": ("Country Delight", "grocery"),

    # Shopping & E-Commerce
    "amazon": ("Amazon", "shopping"),
    "flipkart": ("Flipkart", "shopping"),
    "myntra": ("Myntra", "shopping"),
    "meesho": ("Meesho", "shopping"),
    "ajio": ("AJIO", "shopping"),
    "nykaa": ("Nykaa", "shopping"),
    "tatacliq": ("Tata CLiQ", "shopping"),
    "tata cliq": ("Tata CLiQ", "shopping"),
    "croma": ("Croma", "shopping"),
    "reliance digital": ("Reliance Digital", "shopping"),
    "decathlon": ("Decathlon", "shopping"),
    "zudio": ("Zudio", "shopping"),
    "westside": ("Westside", "shopping"),
    "pantaloons": ("Pantaloons", "shopping"),
    "lifestyle": ("Lifestyle", "shopping"),
    "ikea": ("IKEA", "shopping"),
    "firstcry": ("FirstCry", "shopping"),
    "lenskart": ("Lenskart", "shopping"),

    # Transport & Fuel
    "uber": ("Uber", "transport"),
    "ola": ("Ola", "transport"),
    "rapido": ("Rapido", "transport"),
    "namma yatri": ("Namma Yatri", "transport"),
    "nammayatri": ("Namma Yatri", "transport"),
    "blusmart": ("BluSmart", "transport"),
    "indian oil": ("Indian Oil", "transport"),
    "iocl": ("Indian Oil", "transport"),
    "hpcl": ("HPCL Petrol", "transport"),
    "bpcl": ("BPCL Petrol", "transport"),
    "shell": ("Shell Fuel", "transport"),
    "fastag": ("FASTag", "transport"),
    "bmrc": ("Namma Metro", "transport"),
    "dmrc": ("Delhi Metro", "transport"),

    # Travel & Hospitality
    "irctc": ("IRCTC", "travel"),
    "makemytrip": ("MakeMyTrip", "travel"),
    "mmt": ("MakeMyTrip", "travel"),
    "goibibo": ("Goibibo", "travel"),
    "redbus": ("redBus", "travel"),
    "indigo": ("IndiGo Airlines", "travel"),
    "air india": ("Air India", "travel"),
    "airindia": ("Air India", "travel"),
    "vistara": ("Vistara", "travel"),
    "akasa": ("Akasa Air", "travel"),
    "oyo": ("OYO Rooms", "travel"),
    "airbnb": ("Airbnb", "travel"),
    "cleartrip": ("Cleartrip", "travel"),
    "ixigo": ("ixigo", "travel"),
    "yatra": ("Yatra", "travel"),

    # Bills & Utilities
    "airtel": ("Airtel", "bills"),
    "jio": ("Jio", "bills"),
    "vi ": ("Vi (Vodafone Idea)", "bills"),
    "vodafone": ("Vi (Vodafone Idea)", "bills"),
    "bsnl": ("BSNL", "bills"),
    "act fibernet": ("ACT Fibernet", "bills"),
    "bescom": ("BESCOM Electricity", "bills"),
    "tata power": ("Tata Power", "bills"),
    "tatapower": ("Tata Power", "bills"),
    "adani electricity": ("Adani Electricity", "bills"),
    "mseb": ("MSEB Electricity", "bills"),
    "bwssb": ("BWSSB Water", "bills"),
    "indane": ("Indane Gas", "bills"),
    "hp gas": ("HP Gas", "bills"),
    "bharatgas": ("Bharat Gas", "bills"),
    "tata play": ("Tata Play DTH", "bills"),
    "tataplay": ("Tata Play DTH", "bills"),
    "cred": ("CRED Bill Pay", "bills"),
    "bbps": ("BBPS Utility Bill", "bills"),
    "electricity": ("Electricity Bill", "bills"),

    # Entertainment & Subscriptions
    "netflix": ("Netflix", "entertainment"),
    "bookmyshow": ("BookMyShow", "entertainment"),
    "hotstar": ("Disney+ Hotstar", "entertainment"),
    "jiocinema": ("JioCinema", "entertainment"),
    "spotify": ("Spotify", "entertainment"),
    "prime video": ("Amazon Prime", "entertainment"),
    "sonyliv": ("SonyLIV", "entertainment"),
    "zee5": ("ZEE5", "entertainment"),
    "youtube": ("YouTube Premium", "entertainment"),
    "pvr": ("PVR Inox", "entertainment"),
    "inox": ("PVR Inox", "entertainment"),
    "steam": ("Steam Games", "entertainment"),
    "playstation": ("PlayStation", "entertainment"),

    # Healthcare & Pharmacy
    "apollo": ("Apollo Pharmacy", "healthcare"),
    "pharmeasy": ("PharmEasy", "healthcare"),
    "1mg": ("Tata 1mg", "healthcare"),
    "tata 1mg": ("Tata 1mg", "healthcare"),
    "netmeds": ("Netmeds", "healthcare"),
    "medplus": ("MedPlus", "healthcare"),
    "practo": ("Practo", "healthcare"),
    "manipal": ("Manipal Hospital", "healthcare"),
    "fortis": ("Fortis Healthcare", "healthcare"),
    "max healthcare": ("Max Healthcare", "healthcare"),
    "narayana health": ("Narayana Health", "healthcare"),
    "dr lal pathlabs": ("Dr. Lal PathLabs", "healthcare"),
    "cultfit": ("Cult.fit", "healthcare"),

    # Education (Explicitly highlighted in Project Synopsis)
    "udemy": ("Udemy", "education"),
    "coursera": ("Coursera", "education"),
    "unacademy": ("Unacademy", "education"),
    "byjus": ("BYJU'S", "education"),
    "physicswallah": ("PhysicsWallah", "education"),
    "pw ": ("PhysicsWallah", "education"),
    "upgrad": ("upGrad", "education"),
    "scaler": ("Scaler Academy", "education"),
    "rv university": ("RV University", "education"),
    "university": ("University Fee", "education"),
    "college fee": ("College Tuition", "education"),
    "school fee": ("School Fee", "education"),
    "tuition": ("Tuition Fee", "education"),
    "leetcode": ("LeetCode", "education"),

    # Investment & Wealth
    "zerodha": ("Zerodha", "investment"),
    "groww": ("Groww", "investment"),
    "upstox": ("Upstox", "investment"),
    "angel one": ("Angel One", "investment"),
    "angelone": ("Angel One", "investment"),
    "kuvera": ("Kuvera", "investment"),
    "coin ": ("Zerodha Coin", "investment"),
    "smallcase": ("smallcase", "investment"),
    "indmoney": ("INDmoney", "investment"),
    "lic": ("LIC Insurance", "investment"),
    "sip ": ("Mutual Fund SIP", "investment"),
    "nps": ("National Pension System", "investment"),
}

# Multilingual & Code-Mixed Keywords for Transaction Type (Debit / Credit)
DEBIT_KEYWORDS = [
    # English
    "debited", "debit", "spent", "paid", "charged", "sent", "withdrawn", "purchase",
    "deducted", "payment of", "dr", "dr.", "autopay", "due", "emi of", "transferred to",
    # Hindi (Devanagari & Romanized Hinglish)
    "डेबिट", "काटे गए", "भुगतान", "निकासी", "भेजे गए", "कट गया", "कटे",
    "kat gaya", "kate gaye", "debit hua", "bheje", "nikale", "kharch", "bhugtan", "diya",
    # Telugu
    "డెబిట్", "చెల్లించబడింది", "తీసివేయబడింది",
    # Tamil
    "டெபிட்", "செலுத்தப்பட்டது", "கழிக்கப்பட்டது", "பற்று",
    # Bengali
    "ডেবিট", "কেটে নেওয়া", "প্রদান করা হয়েছে",
    # Kannada
    "ಡೆಬಿಟ್", "ಪಾವತಿಸಲಾಗಿದೆ", "ಕಡಿತಗೊಳಿಸಲಾಗಿದೆ", "ಕಟ್ ಆಗಿದೆ",
]

CREDIT_KEYWORDS = [
    # English
    "credited", "credit", "received", "deposited", "refund", "reversal", "cashback",
    "salary", "cr", "cr.", "added to", "transferred from", "neft from", "imps from",
    # Hindi (Devanagari & Romanized Hinglish)
    "क्रेडिट", "जमा", "प्राप्त", "मिले", "आए", "वापसी",
    "credit hua", "jama hua", "jama", "mila", "mile", "aaye", "aaya", "wapas",
    # Telugu
    "క్రెడిట్", "జమ", "స్వీకరించబడింది",
    # Tamil
    "கிரெடிட்", "வரவு", "பெறப்பட்டது",
    # Bengali
    "ক্রেডিট", "জমা হয়েছে", "প্রাপ্ত",
    # Kannada
    "ಕ್ರೆಡಿಟ್", "ಜಮಾ", "ಸ್ವೀಕರಿಸಲಾಗಿದೆ", "ಬಂದಿದೆ",
]
