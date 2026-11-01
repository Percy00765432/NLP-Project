"""
Multi-Model Expense Categorization Engine & Explainability Module.

Implements and compares the 4 modeling paradigms planned in the Project Synopsis:
1. Rule-Based & Lexicon Classifier (Merchant VPA + Financial Keyword Rules)
2. Support Vector Machine (LinearSVC + Calibrated Probabilities with Word + Character N-Gram TF-IDF,
   inspired by García-Méndez et al., 2020 and Jørgensen & Igel, 2021)
3. Gradient Boosted Decision Trees (LightGBM / Logistic Regression Ensemble on Multilingual Subword TF-IDF)
4. Multilingual Transformer Fine-Tuning & Inference Pipeline (MuRIL `google/muril-base-cased` /
   XLM-RoBERTa `xlm-roberta-base`, Khanuja et al., 2021 & Conneau et al., 2020)

Also includes a Feature-Attribution Explainability Engine (inspired by González-González et al., 2022)
that highlights the top tokens/phrases driving each expense category decision.
"""

import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from src.config import MODELS_DIR, SYNOPSIS_CATEGORY_MAP
from src.extractor import FinancialEntityExtractor
from src.preprocessor import normalize_financial_text


# Category keyword rules for Rule-Based baseline and hybrid fallback
CATEGORY_KEYWORD_RULES: Dict[str, List[str]] = {
    "food": ["swiggy", "zomato", "domino", "kfc", "mcdonald", "starbucks", "pizza", "burger", "restaurant", "cafe", "food", "khana", "eatfit", "faasos", "haldiram"],
    "grocery": ["zepto", "bigbasket", "blinkit", "instamart", "dmart", "jiomart", "grocery", "supermarket", "kirana", "milk", "country delight"],
    "shopping": ["amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa", "tatacliq", "croma", "decathlon", "zudio", "shopping", "mall", "retail", "lenskart"],
    "transport": ["uber", "ola", "rapido", "namma yatri", "metro", "petrol", "fuel", "iocl", "hpcl", "bpcl", "shell", "fastag", "cab", "auto"],
    "travel": ["irctc", "makemytrip", "goibibo", "redbus", "indigo", "air india", "vistara", "oyo", "airbnb", "hotel", "flight", "train", "travel", "cleartrip"],
    "bills": ["airtel", "jio", "vodafone", "bsnl", "bescom", "tata power", "electricity", "water", "gas", "indane", "bharatgas", "broadband", "fibernet", "recharge", "bill", "cesc", "bijli", "cred"],
    "entertainment": ["netflix", "bookmyshow", "hotstar", "jiocinema", "spotify", "prime video", "sonyliv", "pvr", "inox", "movie", "cinema", "steam"],
    "healthcare": ["apollo", "pharmeasy", "1mg", "netmeds", "medplus", "practo", "hospital", "clinic", "pharmacy", "medical", "doctor", "health", "cult.fit", "cultfit", "dawa", "manipal", "fortis"],
    "education": ["udemy", "coursera", "unacademy", "byju", "physicswallah", "pw@", "upgrad", "scaler", "university", "college", "school", "tuition", "course", "education", "shiksha", "शिक्षण"],
    "investment": ["zerodha", "groww", "upstox", "angel one", "icici direct", "icicidirect", "dhan", "paytm money", "paytmmoney", "mutual fund", "sip", "kuvera", "stocks", "nps", "lic"],
    "emi": ["emi", "loan", "bajaj finance", "auto-debit", "equated monthly"],
    "salary": ["salary", "payroll", "stipend", "वेतन", "tankhwah", "pagar"],
    "transfer": ["neft from", "imps to", "imps from", "rtgs", "transferred to", "sent to"],
}


class RuleBasedCategorizer:
    """
    Baseline 1: Rule-based & Lexicon Expense Categorizer.
    Uses extracted merchant/VPA hints and multilingual keyword matching.
    """

    def __init__(self) -> None:
        self.extractor = FinancialEntityExtractor()

    def predict_single(self, text: str, extracted: Optional[Dict[str, Any]] = None) -> Tuple[str, float, List[str]]:
        if extracted is None:
            extracted = self.extractor.extract(text)

        # 1. Check direct merchant lexicon category hint from extractor
        hint = extracted.get("lexicon_category_hint")
        if hint:
            trigger = extracted.get("merchant") or extracted.get("beneficiary") or extracted.get("vpa") or hint
            return hint, 0.95, [f"merchant/vpa:{trigger}"]

        # 2. Check keyword rules
        lower_text = normalize_financial_text(text, expand_multilingual=True).lower()
        for cat, keywords in CATEGORY_KEYWORD_RULES.items():
            for kw in keywords:
                if kw in lower_text:
                    return cat, 0.85, [f"keyword:{kw}"]

        # 3. Heuristic fallback based on P2P vs P2M and credit/debit
        if not extracted.get("is_p2m") and extracted.get("beneficiary"):
            return "transfer", 0.75, [f"beneficiary:{extracted['beneficiary']}"]

        return "shopping", 0.50, ["fallback:default_shopping"]

    def predict(self, texts: List[str]) -> List[str]:
        return [self.predict_single(t)[0] for t in texts]


class ClassicalMLCategorizer:
    """
    Implements Classical & Ensemble ML Categorizers using combined Word N-Gram +
    Character-Level Subword N-Gram TF-IDF representations (handles code-mixing,
    transliteration, spelling variations, and Indian scripts).

    Models trained:
    - `svm`: Calibrated Linear Support Vector Machine (LinearSVC)
    - `logreg`: Multinomial Logistic Regression (MaxEnt)
    - `lightgbm`: LightGBM Gradient Boosted Decision Trees
    """

    def __init__(self) -> None:
        self.vectorizer: Optional[FeatureUnion] = None
        self.models: Dict[str, Any] = {}
        self.classes_: List[str] = []

    def _build_vectorizer(self) -> FeatureUnion:
        word_vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=25000,
            sublinear_tf=True,
            min_df=2,
        )
        # Character n-grams (3 to 5 chars) capture morphological subwords in Indic scripts,
        # VPA handles, and misspelled/code-mixed Hinglish words (Jørgensen & Igel, 2021; Kumar et al., 2023)
        char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=30000,
            sublinear_tf=True,
            min_df=3,
        )
        return FeatureUnion([("word", word_vec), ("char", char_vec)])

    def fit(self, train_texts: List[str], train_labels: List[str]) -> None:
        print("Fitting Word + Character N-Gram TF-IDF Vectorizer...")
        norm_texts = [normalize_financial_text(t, expand_multilingual=True) for t in train_texts]
        self.vectorizer = self._build_vectorizer()
        X_train = self.vectorizer.fit_transform(norm_texts)
        y_train = np.array(train_labels)
        self.classes_ = sorted(list(set(train_labels)))

        # 1. Support Vector Machine (Calibrated LinearSVC)
        print("Training Model 1: Support Vector Machine (LinearSVC + Calibration)...")
        base_svc = LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=3000)
        svm_clf = CalibratedClassifierCV(base_svc, cv=3)
        svm_clf.fit(X_train, y_train)
        self.models["svm"] = svm_clf

        # 2. Multinomial Logistic Regression
        print("Training Model 2: Multinomial Logistic Regression...")
        lr_clf = LogisticRegression(
            C=2.0, class_weight="balanced", max_iter=1000, random_state=42
        )
        lr_clf.fit(X_train, y_train)
        self.models["logreg"] = lr_clf

        # 3. LightGBM Classifier
        try:
            import lightgbm as lgb
            print("Training Model 3: LightGBM Gradient Boosting Classifier...")
            lgb_clf = lgb.LGBMClassifier(
                n_estimators=120,
                learning_rate=0.1,
                num_leaves=31,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )
            lgb_clf.fit(X_train, y_train)
            self.models["lightgbm"] = lgb_clf
        except Exception as e:
            print(f"Skipping LightGBM ({e}); using SVM and LogisticRegression.")

    def predict(self, texts: List[str], model_name: str = "svm") -> np.ndarray:
        norm_texts = [normalize_financial_text(t, expand_multilingual=True) for t in texts]
        X = self.vectorizer.transform(norm_texts)
        clf = self.models[model_name]
        return clf.predict(X)

    def predict_proba(self, texts: List[str], model_name: str = "svm") -> np.ndarray:
        norm_texts = [normalize_financial_text(t, expand_multilingual=True) for t in texts]
        X = self.vectorizer.transform(norm_texts)
        clf = self.models[model_name]
        return clf.predict_proba(X)

    def explain_prediction(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Extracts the top contributing words/subwords for the predicted category
        using linear model weights * TF-IDF activations (Explainable NLP, González-González et al., 2022).
        """
        if not self.vectorizer or "logreg" not in self.models:
            return []

        norm_text = normalize_financial_text(text, expand_multilingual=True)
        X_vec = self.vectorizer.transform([norm_text])
        lr_model: LogisticRegression = self.models["logreg"]
        pred_class = lr_model.predict(X_vec)[0]
        class_idx = list(lr_model.classes_).index(pred_class)

        # Retrieve feature names from word vectorizer first for human-readable rationales
        word_vec: TfidfVectorizer = self.vectorizer.transformer_list[0][1]
        word_features = word_vec.get_feature_names_out()
        n_word_feats = len(word_features)

        coefs = lr_model.coef_[class_idx][:n_word_feats]
        x_word = X_vec[:, :n_word_feats].toarray()[0]
        contributions = x_word * coefs

        nonzero_indices = np.where(contributions > 0)[0]
        sorted_idx = nonzero_indices[np.argsort(-contributions[nonzero_indices])][:top_k]

        rationales = []
        for idx in sorted_idx:
            rationales.append({
                "token": str(word_features[idx]),
                "weight": round(float(contributions[idx]), 4),
            })
        return rationales

    def save(self, path: Optional[Path] = None) -> Path:
        target = path or (MODELS_DIR / "classical_categorizers.pkl")
        with open(target, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "models": self.models,
                    "classes": self.classes_,
                },
                f,
            )
        return target

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "ClassicalMLCategorizer":
        import sys
        import types

        target = path or (MODELS_DIR / "classical_categorizers.pkl")
        obj = cls()
        try:
            with open(target, "rb") as f:
                data = pickle.load(f)
        except OSError:
            # Fallback on macOS if libomp.dylib is not installed for LightGBM
            lgb_stub = types.ModuleType("lightgbm")
            lgb_stub.LGBMClassifier = type("LGBMClassifier", (), {})
            lgb_stub.Booster = type("Booster", (), {})
            sys.modules["lightgbm"] = lgb_stub
            sys.modules["lightgbm.sklearn"] = lgb_stub
            sys.modules["lightgbm.basic"] = lgb_stub
            with open(target, "rb") as f:
                data = pickle.load(f)
            if "lightgbm" in data.get("models", {}):
                del data["models"]["lightgbm"]

        obj.vectorizer = data["vectorizer"]
        obj.models = data["models"]
        obj.classes_ = data["classes"]
        return obj


class MultilingualTransformerCategorizer:
    """
    Fine-tunes or runs a Hugging Face Multilingual Transformer backbone
    (supports `google/muril-base-cased`, `xlm-roberta-base`, or `distilbert-base-multilingual-cased`)
    on Apple Silicon (MPS), CUDA, or CPU.
    """

    def __init__(self, model_name_or_path: str = "distilbert-base-multilingual-cased") -> None:
        self.model_name_or_path = model_name_or_path
        self.label2id: Dict[str, int] = {}
        self.id2label: Dict[int, str] = {}
        self.tokenizer = None
        self.model = None
        self.device = "cpu"

    def train_and_save(
        self,
        train_texts: List[str],
        train_labels: List[str],
        val_texts: List[str],
        val_labels: List[str],
        epochs: int = 2,
        batch_size: int = 32,
        max_length: int = 96,
        lr: float = 3e-5,
        save_dir: Optional[Path] = None,
    ) -> Dict[str, float]:
        import torch
        from torch.utils.data import Dataset, DataLoader
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        from sklearn.metrics import accuracy_score, f1_score

        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        unique_labels = sorted(list(set(train_labels)))
        self.label2id = {lbl: idx for idx, lbl in enumerate(unique_labels)}
        self.id2label = {idx: lbl for lbl, idx in self.label2id.items()}

        print(f"Loading Multilingual Transformer '{self.model_name_or_path}' on device={self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name_or_path,
            num_labels=len(unique_labels),
            id2label=self.id2label,
            label2id=self.label2id,
        ).to(self.device)

        class SMSDataset(Dataset):
            def __init__(self, texts: List[str], labels: List[str], tokenizer: Any, l2i: Dict[str, int]) -> None:
                self.encodings = tokenizer(
                    texts, truncation=True, padding=True, max_length=max_length, return_tensors="pt"
                )
                self.labels = torch.tensor([l2i[y] for y in labels], dtype=torch.long)

            def __len__(self) -> int:
                return len(self.labels)

            def __getitem__(self, idx: int) -> Dict[str, Any]:
                item = {k: v[idx] for k, v in self.encodings.items()}
                item["labels"] = self.labels[idx]
                return item

        train_ds = SMSDataset(train_texts, train_labels, self.tokenizer, self.label2id)
        val_ds = SMSDataset(val_texts, val_labels, self.tokenizer, self.label2id)

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size * 2, shuffle=False)

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=0.01)

        for epoch in range(epochs):
            self.model.train()
            total_loss = 0.0
            for batch in train_loader:
                optimizer.zero_grad()
                inputs = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**inputs)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / max(len(train_loader), 1)
            print(f"Epoch {epoch + 1}/{epochs} - Train Loss: {avg_loss:.4f}")

        # Evaluate on validation set
        self.model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for batch in val_loader:
                labels = batch.pop("labels").numpy()
                inputs = {k: v.to(self.device) for k, v in batch.items()}
                logits = self.model(**inputs).logits
                pred_ids = torch.argmax(logits, dim=-1).cpu().numpy()
                preds.extend([self.id2label[int(i)] for i in pred_ids])
                trues.extend([self.id2label[int(i)] for i in labels])

        val_acc = float(accuracy_score(trues, preds))
        val_f1 = float(f1_score(trues, preds, average="macro", zero_division=0))

        out_dir = save_dir or (MODELS_DIR / "multilingual_transformer")
        out_dir.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(out_dir)
        self.tokenizer.save_pretrained(out_dir)
        print(f"Saved Multilingual Transformer to {out_dir} (Val Acc: {val_acc:.4f}, Macro F1: {val_f1:.4f})")
        return {"val_accuracy": val_acc, "val_macro_f1": val_f1}

    @classmethod
    def load(cls, model_dir: Optional[Path] = None) -> Optional["MultilingualTransformerCategorizer"]:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        target = model_dir or (MODELS_DIR / "multilingual_transformer")
        if not target.exists():
            return None
        obj = cls(str(target))
        if torch.backends.mps.is_available():
            obj.device = "mps"
        elif torch.cuda.is_available():
            obj.device = "cuda"
        else:
            obj.device = "cpu"
        obj.tokenizer = AutoTokenizer.from_pretrained(target)
        obj.model = AutoModelForSequenceClassification.from_pretrained(target).to(obj.device)
        obj.model.eval()
        obj.id2label = {int(k): v for k, v in obj.model.config.id2label.items()}
        obj.label2id = {v: int(k) for k, v in obj.id2label.items()}
        return obj

    def predict(self, texts: List[str], batch_size: int = 64) -> List[str]:
        import torch

        if self.model is None or self.tokenizer is None:
            raise RuntimeError("MultilingualTransformerCategorizer is not loaded.")

        preds: List[str] = []
        self.model.eval()
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                enc = self.tokenizer(
                    batch_texts, truncation=True, padding=True, max_length=96, return_tensors="pt"
                ).to(self.device)
                logits = self.model(**enc).logits
                pred_ids = torch.argmax(logits, dim=-1).cpu().numpy()
                preds.extend([self.id2label[int(idx)] for idx in pred_ids])
        return preds

    def predict_single_with_confidence(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        import torch

        self.model.eval()
        with torch.no_grad():
            enc = self.tokenizer(
                [text], truncation=True, padding=True, max_length=96, return_tensors="pt"
            ).to(self.device)
            logits = self.model(**enc).logits[0]
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            top_idx = int(np.argmax(probs))
            top_label = self.id2label[top_idx]
            top_conf = float(probs[top_idx])
            all_scores = {self.id2label[i]: round(float(probs[i]), 4) for i in range(len(probs))}
        return top_label, top_conf, all_scores


class HybridTransactionPipeline:
    """
    End-to-End Unified Pipeline combining:
    1. Multilingual & Code-Mixed Preprocessing
    2. Hybrid Financial Entity Extraction (Amount, Type, Bank, Account, Date, Merchant, VPA, Reference)
    3. Ensemble Expense Categorization (combining High-Precision Merchant Lexicon + SVM/LightGBM + Multilingual Transformer)
    4. Explainable AI Rationales (top contributing tokens + matched rules)
    """

    def __init__(self, load_transformer: bool = True) -> None:
        self.extractor = FinancialEntityExtractor()
        self.rule_model = RuleBasedCategorizer()
        self.classical_model: Optional[ClassicalMLCategorizer] = None
        self.transformer_model: Optional[MultilingualTransformerCategorizer] = None

        if (MODELS_DIR / "classical_categorizers.pkl").exists():
            self.classical_model = ClassicalMLCategorizer.load()

        if load_transformer and (MODELS_DIR / "multilingual_transformer").exists():
            try:
                self.transformer_model = MultilingualTransformerCategorizer.load()
            except Exception:
                self.transformer_model = None

    def process_message(self, text: str, preferred_classifier: str = "hybrid_ensemble") -> Dict[str, Any]:
        """
        Processes a raw financial message and returns all extracted entities,
        expense category (fine-grained + Synopsis high-level), confidence score,
        and explainable rationales.
        """
        extracted = self.extractor.extract(text)
        raw_sms = extracted["raw_sms"]
        norm_text = normalize_financial_text(raw_sms, expand_multilingual=True)

        rule_cat, rule_conf, rule_reasons = self.rule_model.predict_single(raw_sms, extracted=extracted)
        explanations = list(rule_reasons)
        category_probabilities: Dict[str, float] = {}

        # Model selection
        if preferred_classifier == "rule_based" or self.classical_model is None:
            final_cat = rule_cat
            final_conf = rule_conf
            model_used = "Rule-Based Lexicon"
        elif preferred_classifier in {"svm", "logreg", "lightgbm"}:
            m_key = preferred_classifier if preferred_classifier in self.classical_model.models else "svm"
            probs = self.classical_model.predict_proba([raw_sms], model_name=m_key)[0]
            classes = self.classical_model.models[m_key].classes_
            top_idx = int(np.argmax(probs))
            final_cat = str(classes[top_idx])
            final_conf = float(probs[top_idx])
            category_probabilities = {str(classes[i]): round(float(probs[i]), 4) for i in range(len(classes))}
            model_used = f"Classical ML ({m_key.upper()})"
        elif preferred_classifier == "transformer" and self.transformer_model is not None:
            final_cat, final_conf, category_probabilities = (
                self.transformer_model.predict_single_with_confidence(norm_text)
            )
            model_used = "Multilingual Transformer"
        else:
            # Hybrid Ensemble: Combine High-Precision Entity Lexicon + Calibrated SVM + Transformer (if loaded)
            probs_svm = self.classical_model.predict_proba([raw_sms], model_name="svm")[0]
            classes = list(self.classical_model.models["svm"].classes_)
            combined_scores = {str(classes[i]): float(probs_svm[i]) for i in range(len(classes))}

            if self.transformer_model is not None:
                _, _, trans_probs = self.transformer_model.predict_single_with_confidence(norm_text)
                for k, v in trans_probs.items():
                    combined_scores[k] = 0.5 * combined_scores.get(k, 0.0) + 0.5 * v
                model_used = "Hybrid Ensemble (Lexicon + SVM + Multilingual Transformer)"
            else:
                model_used = "Hybrid Ensemble (Lexicon + Subword SVM)"

            # Boost if unambiguous merchant lexicon hit exists
            if extracted.get("lexicon_category_hint"):
                hint_cat = extracted["lexicon_category_hint"]
                combined_scores[hint_cat] = combined_scores.get(hint_cat, 0.0) + 0.65

            total_s = sum(combined_scores.values()) or 1.0
            category_probabilities = {k: round(v / total_s, 4) for k, v in combined_scores.items()}
            final_cat = max(category_probabilities.items(), key=lambda x: x[1])[0]
            final_conf = category_probabilities[final_cat]

        # Add token-level feature attributions from linear model
        if self.classical_model is not None:
            token_attr = self.classical_model.explain_prediction(raw_sms, top_k=4)
            for item in token_attr:
                explanations.append(f"token:{item['token']} (+{item['weight']:.2f})")

        synopsis_cat = SYNOPSIS_CATEGORY_MAP.get(final_cat, "Shopping")

        return {
            **extracted,
            "category": final_cat,
            "synopsis_category": synopsis_cat,
            "confidence": round(final_conf, 4),
            "model_used": model_used,
            "explanations": explanations,
            "category_probabilities": category_probabilities,
        }
