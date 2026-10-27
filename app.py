"""
Streamlit Interactive Expense Tracker & Financial NLP Workbench
Title: Robust NLP Framework for Automated Financial Transaction Extraction and Expense Categorization
Team ID: 10 | School of Computer Science and Engineering, RV University
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    DATA_DIR,
    OUTPUTS_DIR,
    SUPPORTED_LANGUAGES,
    SYNOPSIS_CATEGORY_MAP,
)
from src.categorizer import HybridTransactionPipeline


st.set_page_config(
    page_title="FinNLP — Automated Financial Transaction Extraction & Expense Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for NER Badges & Cards
ENTITY_COLORS = {
    "BANK": ("#dbeafe", "#1e40af"),
    "ACCOUNT": ("#e0e7ff", "#3730a3"),
    "AMOUNT": ("#dcfce7", "#166534"),
    "DATE": ("#fef3c7", "#92400e"),
    "MERCHANT": ("#fce7f3", "#9d174d"),
    "BENEFICIARY": ("#f3e8ff", "#6b21a8"),
    "VPA": ("#ffedd5", "#9a3412"),
    "REFERENCE": ("#f1f5f9", "#334155"),
}


@st.cache_resource
def get_pipeline() -> HybridTransactionPipeline:
    return HybridTransactionPipeline(load_transformer=True)


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    test_parquet = DATA_DIR / "test_processed.parquet"
    if test_parquet.exists():
        return pd.read_parquet(test_parquet)
    sample_csv = DATA_DIR / "sample_test_500.csv"
    if sample_csv.exists():
        return pd.read_csv(sample_csv)
    return pd.DataFrame()


@st.cache_data
def load_eval_report() -> Dict[str, Any]:
    report_file = OUTPUTS_DIR / "evaluation_report.json"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def render_annotated_sms(raw_sms: str, spans: List[Dict[str, Any]]) -> str:
    """Renders inline HTML with colored NER entity badges for visual inspection."""
    if not spans:
        return f"<div style='padding:14px;background:#f8fafc;border-radius:8px;font-family:monospace;'>{raw_sms}</div>"

    html_parts = []
    last_idx = 0
    for sp in sorted(spans, key=lambda x: x["start"]):
        start, end = sp["start"], sp["end"]
        if start < last_idx:
            continue
        html_parts.append(raw_sms[last_idx:start])
        bg, fg = ENTITY_COLORS.get(sp["label"], ("#e2e8f0", "#1e293b"))
        span_text = raw_sms[start:end]
        badge = (
            f"<span style='background-color:{bg};color:{fg};padding:3px 8px;border-radius:6px;"
            f"font-weight:600;margin:0 2px;display:inline-block;border:1px solid {fg}33;'>"
            f"{span_text} <sub style='font-size:0.68em;text-transform:uppercase;opacity:0.85;'>{sp['label']}</sub>"
            f"</span>"
        )
        html_parts.append(badge)
        last_idx = end

    html_parts.append(raw_sms[last_idx:])
    joined = "".join(html_parts)
    return (
        f"<div style='padding:18px;background:#ffffff;border:1px solid #e2e8f0;"
        f"border-radius:10px;line-height:2.1;font-size:1.05rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);'>"
        f"{joined}</div>"
    )


# Curated Preset Examples across English, 5 Indian Scripts, and Code-Mixed Hinglish/Kanglish/Tanglish
PRESET_EXAMPLES = {
    "English — Healthcare (UPI / Netmeds)": (
        "HDFC Bank: Rs.7,361.93 debited from A/c XX1489 on 03-11-25. VPA netmeds@icici. UPI Ref: 549264265572. Not you? Call 18002586161"
    ),
    "English — Education (RV University Tuition Fee)": (
        "SBI: INR 65,000.00 paid from A/c XX4821 on 14-08-2025 towards RV University Tuition Fee. VPA rvuniversity@sbi. Ref: 839201746512. Avl Bal: Rs.1,12,450"
    ),
    "Hinglish (Code-Mixed) — Food Delivery (Swiggy)": (
        "HDFC Bank Alert: Aapke A/c XX4248 se Rs.485.50 kat gaya for Swiggy payment on 28-04-2025 to swiggy@ybl. UPI Ref: 430298465323. Avl Bal Rs.18,420"
    ),
    "Hinglish (Code-Mixed) — P2P Credit": (
        "Dear Customer, aapke SBI khate XX9012 mein Rs.15,000.00 credit hua on 19-09-2025 from rahul.sharma@okaxis. Ref 918273645510."
    ),
    "Kanglish (Kannada Code-Mixed) — Shopping (Myntra)": (
        "ICICI Alert: Nimma A/c XX3319 inda Rs.2,499.00 Myntra ge UPI mulaka debit agide on 12-10-2025. VPA myntra@ybl. Ref: 617283940112"
    ),
    "Tanglish (Tamil Code-Mixed) — Transport (Uber)": (
        "Axis Bank: Unga A/c XX7741 la irundhu Rs.340.00 Uber ku debit aagiduchu on 05-10-2025. VPA uber@axis. UPI Ref: 728394019283"
    ),
    "Hindi (हिंदी) — Food / UPI": (
        "HDFC: आपके खाते XX4248 से Rs.268.73 डेबिट हुआ। दिनांक 28-04-2025। swiggy@ybl। संदर्भ: 430298465323"
    ),
    "Kannada (ಕನ್ನಡ) — Bank Debit Notification": (
        "HDFC: ನಿಮ್ಮ ಖಾತೆ XX5059 ನಿಂದ Rs.530.87 ಡೆಬಿಟ್ ಆಗಿದೆ. ದಿನಾಂಕ 02-02-2025. zepto@ybl. Ref: 000359529957"
    ),
    "Telugu (తెలుగు) — E-Commerce Shopping": (
        "HDFC: మీ ఖాతా XX9731 నుండి Rs.403.06 డెబిట్ చేయబడింది. తేదీ 03-02-2025. amazon@ybl. Ref: 864907792778"
    ),
    "Tamil (தமிழ்) — Bank Notification": (
        "HDFC: உங்கள் கணக்கு XX6623 இல் இருந்து Rs.269.83 டெபிட் செய்யப்பட்டது. தேதி 03-03-2025. irctc@sbi. Ref: 822283029881"
    ),
    "Bengali (বাংলা) — Bank Debit Alert": (
        "HDFC: আপনার অ্যাকাউন্ট XX4385 থেকে Rs.940.23 ডেবিট হয়েছে। তারিখ 11-08-2025। apollo@hdfcbank। Ref: 764883136364"
    ),
    "English — Investment (Zerodha Broking)": (
        "YES Bank: Rs.35,442.09 debited from A/c XX8306 on 07-Mar-25. UPI/zerodha@hdfcbank. Ref: 906063582611"
    ),
}


def main() -> None:
    pipeline = get_pipeline()
    df_test = load_sample_data()
    eval_report = load_eval_report()

    # Sidebar Header & Project Metadata
    with st.sidebar:
        st.markdown("## 🏦 FinNLP Framework")
        st.caption(
            "**Robust NLP Framework for Automated Financial Transaction Extraction & Expense Categorization**"
        )
        st.markdown("---")
        classifier_choice = st.selectbox(
            "Select Categorization Engine",
            options=[
                ("hybrid_ensemble", "Hybrid Ensemble (Lexicon + Subword SVM + Transformer)"),
                ("svm", "Support Vector Machine (Word + Char TF-IDF)"),
                ("lightgbm", "LightGBM Gradient Boosting"),
                ("logreg", "Multinomial Logistic Regression"),
                ("rule_based", "Rule-Based Lexicon Baseline"),
            ],
            format_func=lambda x: x[1],
        )[0]

        st.markdown("---")
        st.markdown("### 🎓 RV University — Team 10")
        st.markdown(
            """
            - **Preksha P V** (`1RUA24CSE0331`)
            - **Reshma K P** (`1RUA24CSE0363`)
            - **Prathik K B** (`1RUA24CSE0327`)
            - **Rushil Ravi Reddy** (`1RUA24CSE0380`)
            
            **Guides:**
            - Prof. Khushboo Pandey
            - Prof. Priyanka S Shivaramaiah
            """
        )
        st.markdown("---")
        st.caption("Dataset: [Ranjit0034/finee-dataset](https://huggingface.co/datasets/Ranjit0034/finee-dataset) (152K+ samples, 6 Indian languages + Code-Mixed)")

    st.title("💳 Multilingual Financial Transaction Extractor & Expense Tracker")
    st.markdown(
        "Automatically extract structured entities (**Amount, Merchant/Beneficiary, Bank, Account, Date, VPA, Reference ID**) "
        "and categorize expenses across **English, Hindi, Kannada, Tamil, Telugu, Bengali, and Code-Mixed (Hinglish/Kanglish/Tanglish)** messages."
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Live SMS Extractor & Explainable AI",
        "📊 Personal Expense Tracker & Batch Analyzer",
        "🌐 Multilingual & Code-Mixed Explorer",
        "📈 Model Benchmarks & Evaluation Report",
    ])

    # =========================================================================
    # TAB 1: LIVE SMS EXTRACTOR & EXPLAINABLE AI
    # =========================================================================
    with tab1:
        col_preset, col_lang = st.columns([3, 1])
        with col_preset:
            selected_preset = st.selectbox(
                "Choose a sample banking/UPI message (or type your own below):",
                options=list(PRESET_EXAMPLES.keys()),
            )
        default_sms = PRESET_EXAMPLES[selected_preset]

        sms_input = st.text_area(
            "Input Financial Transaction Message (English / Indic / Code-Mixed):",
            value=default_sms,
            height=95,
        )

        if sms_input.strip():
            result = pipeline.process_message(sms_input, preferred_classifier=classifier_choice)

            st.markdown("#### 1. Named Entity Recognition (NER) & Pattern Span Highlighting")
            st.markdown(
                render_annotated_sms(result["raw_sms"], result["entity_spans"]),
                unsafe_allow_html=True,
            )

            st.markdown("#### 2. Extracted Structured Financial Summary")
            m1, m2, m3, m4, m5 = st.columns(5)
            amt_disp = f"₹{result['amount']:,.2f}" if result["amount"] is not None else "N/A"
            m1.metric("Transaction Amount", amt_disp, delta=result["type"].upper())
            m2.metric("Synopsis Category", result["synopsis_category"], delta=f"FineE: {result['category']}")
            party_label = result["merchant"] or result["beneficiary"] or "Unknown"
            party_type = "Merchant (P2M)" if result["is_p2m"] else "Beneficiary (P2P)"
            m3.metric("Counterparty", party_label, delta=party_type)
            m4.metric("Bank & Account", f"{result['bank'] or 'Bank'} (XX{result['account'] or '----'})", delta=result["payment_mode"])
            lang_label = SUPPORTED_LANGUAGES.get(result["language"], result["language"])
            cm_badge = "Code-Mixed" if result["is_code_mixed"] else "Monolingual"
            m5.metric("Language Detected", lang_label.split("(")[0].strip(), delta=cm_badge)

            col_json, col_explain = st.columns([1.1, 1.1])
            with col_json:
                st.markdown("##### 📄 FinEE Standardized JSON Output")
                clean_json = {
                    "amount": result["amount"],
                    "type": result["type"],
                    "bank": result["bank"],
                    "account": result["account"],
                    "date": result["date"],
                    "reference": result["reference"],
                    "vpa": result["vpa"],
                    "merchant": result["merchant"],
                    "beneficiary": result["beneficiary"],
                    "payment_mode": result["payment_mode"],
                    "category": result["category"],
                    "synopsis_category": result["synopsis_category"],
                    "is_p2m": result["is_p2m"],
                    "language": result["language"],
                    "is_code_mixed": result["is_code_mixed"],
                    "confidence": result["confidence"],
                }
                st.json(clean_json)

            with col_explain:
                st.markdown("##### 🧠 Explainable AI (XAI) Categorization Rationale")
                st.info(f"**Active Engine:** `{result['model_used']}` (Confidence: **{result['confidence']*100:.1f}%**)")
                if result["explanations"]:
                    st.markdown("**Top Decision Rationales (Lexicon Triggers & TF-IDF Feature Attributions):**")
                    for exp in result["explanations"]:
                        st.markdown(f"- `{exp}`")

                if result["category_probabilities"]:
                    probs_df = (
                        pd.DataFrame(
                            list(result["category_probabilities"].items()),
                            columns=["Category", "Probability"],
                        )
                        .sort_values("Probability", ascending=True)
                        .tail(6)
                    )
                    fig_prob = px.bar(
                        probs_df,
                        x="Probability",
                        y="Category",
                        orientation="h",
                        title="Top Predicted Category Probabilities",
                        text_auto=".1%",
                        color="Probability",
                        color_continuous_scale="Tealgrn",
                    )
                    fig_prob.update_layout(height=270, margin=dict(l=10, r=10, t=35, b=10), showlegend=False)
                    st.plotly_chart(fig_prob, use_container_width=True)

    # =========================================================================
    # TAB 2: PERSONAL EXPENSE TRACKER & BATCH ANALYZER
    # =========================================================================
    with tab2:
        st.markdown("### 📊 Automated Personal Expense Tracker Dashboard")
        st.markdown(
            "Analyze a batch of bank/UPI SMS messages from the **FinEE test split** or paste/upload your own transaction log to visualize spending."
        )

        col_ctrl1, col_ctrl2 = st.columns([1, 2])
        with col_ctrl1:
            sample_count = st.slider("Number of transactions to analyze:", min_value=50, max_value=500, value=200, step=50)
            filter_debits = st.checkbox("Show only Expense (Debit) transactions in charts", value=True)

        if not df_test.empty:
            df_batch = df_test.head(sample_count).copy()
            # Ensure synopsis_category is populated
            df_batch["synopsis_category"] = df_batch["category"].map(
                lambda c: SYNOPSIS_CATEGORY_MAP.get(str(c), "Shopping")
            )
            df_expenses = df_batch[df_batch["type"] == "debit"].copy() if filter_debits else df_batch.copy()

            total_debit = df_batch[df_batch["type"] == "debit"]["amount"].sum()
            total_credit = df_batch[df_batch["type"] == "credit"]["amount"].sum()
            num_txns = len(df_batch)
            top_cat = (
                df_expenses.groupby("synopsis_category")["amount"].sum().idxmax()
                if not df_expenses.empty
                else "N/A"
            )

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Spend (Debits)", f"₹{total_debit:,.2f}")
            k2.metric("Total Income/Credits", f"₹{total_credit:,.2f}")
            k3.metric("Transactions Processed", f"{num_txns:,}")
            k4.metric("Highest Spend Category", top_cat)

            c_left, c_right = st.columns(2)
            with c_left:
                cat_spend = (
                    df_expenses.groupby("synopsis_category", as_index=False)["amount"]
                    .sum()
                    .sort_values("amount", ascending=False)
                )
                fig_pie = px.pie(
                    cat_spend,
                    names="synopsis_category",
                    values="amount",
                    hole=0.45,
                    title="Expense Distribution by Synopsis Category (INR)",
                )
                fig_pie.update_layout(height=380)
                st.plotly_chart(fig_pie, use_container_width=True)

            with c_right:
                fine_spend = (
                    df_expenses.groupby("category", as_index=False)["amount"]
                    .agg(total_amount="sum", count="count")
                    .sort_values("total_amount", ascending=True)
                )
                fig_bar = px.bar(
                    fine_spend,
                    x="total_amount",
                    y="category",
                    orientation="h",
                    color="count",
                    title="Fine-Grained FinEE Category Spend & Transaction Count",
                    labels={"total_amount": "Total Amount (₹)", "category": "Category", "count": "Txns"},
                )
                fig_bar.update_layout(height=380)
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### 📋 Structured Transaction Ledger")
            display_cols = [
                "raw_sms", "amount", "type", "synopsis_category", "category",
                "merchant", "beneficiary", "bank", "account", "date", "language", "is_code_mixed",
            ]
            avail_cols = [c for c in display_cols if c in df_batch.columns]
            st.dataframe(df_batch[avail_cols], use_container_width=True, height=320)

            csv_bytes = df_batch[avail_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Categorized Expense Ledger (CSV)",
                data=csv_bytes,
                file_name="categorized_expenses.csv",
                mime="text/csv",
            )

    # =========================================================================
    # TAB 3: MULTILINGUAL & CODE-MIXED EXPLORER
    # =========================================================================
    with tab3:
        st.markdown("### 🌐 Multilingual & Code-Mixed Financial Message Support")
        st.markdown(
            "Supports **6 Indian languages (English, Hindi, Kannada, Tamil, Telugu, Bengali)** plus **Romanized Code-Mixed (Hinglish, Kanglish, Tanglish)** banking messages."
        )
        if not df_test.empty:
            lang_pick = st.selectbox(
                "Filter Dataset Samples by Language / Script:",
                options=list(SUPPORTED_LANGUAGES.keys()),
                format_func=lambda k: f"{SUPPORTED_LANGUAGES[k]} [{k}]",
            )
            sub_lang = df_test[df_test["language"] == lang_pick]
            st.write(f"Showing **{len(sub_lang)}** test samples for **{SUPPORTED_LANGUAGES[lang_pick]}**:")
            if not sub_lang.empty:
                st.dataframe(
                    sub_lang[["raw_sms", "amount", "type", "category", "synopsis_category", "bank", "is_code_mixed"]].head(30),
                    use_container_width=True,
                )

    # =========================================================================
    # TAB 4: MODEL BENCHMARKS & EVALUATION REPORT
    # =========================================================================
    with tab4:
        st.markdown("### 📈 Experimental Evaluation & Model Comparison")
        if eval_report:
            st.markdown("#### 1. Expense Categorization Model Comparison")
            models_tbl = pd.DataFrame.from_dict(eval_report["expense_categorization"]["overall_models"], orient="index")
            models_tbl = models_tbl.reset_index().rename(columns={"index": "Model Architecture"})
            for col in ["accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"]:
                models_tbl[col] = (models_tbl[col] * 100).round(2).astype(str) + "%"
            st.table(models_tbl)

            st.markdown("#### 2. Financial Entity Extraction (NER + Regex) Performance")
            ext_tbl = pd.DataFrame.from_dict(eval_report["entity_extraction"], orient="index")
            ext_tbl = ext_tbl.reset_index().rename(columns={"index": "Entity Field"})
            for col in ["precision", "recall", "f1_score"]:
                ext_tbl[col] = (ext_tbl[col] * 100).round(2).astype(str) + "%"
            st.table(ext_tbl)

            st.markdown("#### 3. Visual Performance Charts")
            c1, c2 = st.columns(2)
            with c1:
                if (OUTPUTS_DIR / "model_comparison.png").exists():
                    st.image(str(OUTPUTS_DIR / "model_comparison.png"), caption="Model Comparison on FinEE Test Set")
                if (OUTPUTS_DIR / "multilingual_performance.png").exists():
                    st.image(str(OUTPUTS_DIR / "multilingual_performance.png"), caption="Multilingual & Code-Mixed Accuracy Breakdown")
            with c2:
                if (OUTPUTS_DIR / "entity_extraction_f1.png").exists():
                    st.image(str(OUTPUTS_DIR / "entity_extraction_f1.png"), caption="Entity Extraction Precision, Recall & F1")
                if (OUTPUTS_DIR / "confusion_matrix.png").exists():
                    st.image(str(OUTPUTS_DIR / "confusion_matrix.png"), caption="Normalized Category Confusion Matrix")
        else:
            st.warning("Run `python train_and_evaluate.py` first to generate evaluation metrics and plots.")


if __name__ == "__main__":
    main()
