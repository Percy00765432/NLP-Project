"""
Streamlit Interactive Expense Tracker, Financial NLP Workbench & iPhone Shortcuts Webhook Server
Title: Robust NLP Framework for Automated Financial Transaction Extraction and Expense Categorization
Team ID: 10 | School of Computer Science and Engineering, RV University
"""

import json
import socket
import threading
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Any, List, Optional

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

IPHONE_LEDGER_PATH = DATA_DIR / "iphone_synced_ledger.json"
WEBHOOK_PORT = 8502


def get_local_wifi_ip() -> str:
    """Detects the Mac's active LAN/Wi-Fi IPv4 address so an iPhone on the same network can reach it."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def load_iphone_ledger() -> List[Dict[str, Any]]:
    if IPHONE_LEDGER_PATH.exists():
        try:
            with open(IPHONE_LEDGER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def append_to_iphone_ledger(entry: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ledger = load_iphone_ledger()
    if ledger and ledger[0].get("raw_sms") == entry.get("raw_sms"):
        return
    ledger.insert(0, entry)
    with open(IPHONE_LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


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


@st.cache_resource
def start_iphone_webhook_server() -> int:
    """
    Starts a lightweight background HTTP JSON API server on port 8502 (or next available port)
    so iPhone Shortcuts can send a POST or GET request directly with `Get Contents of URL`
    and receive clean JSON (`amount`, `category`, `merchant`, `bank`, etc.) while logging to Mac.
    """
    pipeline = get_pipeline()

    class ShortcutWebhookHandler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, payload: Dict[str, Any]):
            body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            sms_text = qs.get("sms", [""])[0].strip()
            model_choice = qs.get("model", ["hybrid_ensemble"])[0].strip()

            if parsed.path in ("/api/ledger", "/ledger"):
                self._send_json(200, {"status": "ok", "count": len(load_iphone_ledger()), "transactions": load_iphone_ledger()})
                return

            if not sms_text:
                self._send_json(200, {
                    "status": "online",
                    "service": "FinNLP macOS & iPhone Shortcuts Server (Cloudflare Tunnel Ready)",
                    "usage": "Send GET /ingest?sms=<message> or POST /api/extract with JSON {'sms': '<message>'}",
                })
                return

            res = pipeline.process_message(sms_text, preferred_classifier=model_choice)
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_device": "iPhone Shortcut (GET)",
                "raw_sms": res["raw_sms"],
                "amount": res["amount"],
                "type": res["type"],
                "category": res["category"],
                "synopsis_category": res["synopsis_category"],
                "merchant": res["merchant"],
                "beneficiary": res["beneficiary"],
                "bank": res["bank"],
                "account": res["account"],
                "date": res["date"],
                "reference": res["reference"],
                "vpa": res["vpa"],
                "language": res["language"],
                "is_code_mixed": res["is_code_mixed"],
                "confidence": res["confidence"],
            }
            append_to_iphone_ledger(record)
            self._send_json(200, {"status": "ok", "transaction": record})

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace") if content_len > 0 else ""
            sms_text = ""
            model_choice = "hybrid_ensemble"

            try:
                data = json.loads(raw_body)
                if isinstance(data, dict):
                    sms_text = str(data.get("sms") or data.get("text") or data.get("message") or "").strip()
                    model_choice = str(data.get("model", "hybrid_ensemble")).strip()
            except Exception:
                qs = urllib.parse.parse_qs(raw_body)
                if "sms" in qs:
                    sms_text = qs["sms"][0].strip()
                else:
                    sms_text = raw_body.strip()

            if not sms_text:
                self._send_json(400, {"status": "error", "message": "Missing 'sms' field in request body"})
                return

            res = pipeline.process_message(sms_text, preferred_classifier=model_choice)
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_device": "iPhone Shortcut (POST)",
                "raw_sms": res["raw_sms"],
                "amount": res["amount"],
                "type": res["type"],
                "category": res["category"],
                "synopsis_category": res["synopsis_category"],
                "merchant": res["merchant"],
                "beneficiary": res["beneficiary"],
                "bank": res["bank"],
                "account": res["account"],
                "date": res["date"],
                "reference": res["reference"],
                "vpa": res["vpa"],
                "language": res["language"],
                "is_code_mixed": res["is_code_mixed"],
                "confidence": res["confidence"],
            }
            append_to_iphone_ledger(record)
            self._send_json(200, {"status": "ok", "transaction": record})

        def log_message(self, format, *args):
            pass

    for port_candidate in [WEBHOOK_PORT, 8503, 8504]:
        try:
            server = HTTPServer(("0.0.0.0", port_candidate), ShortcutWebhookHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            return port_candidate
        except OSError:
            continue
    return WEBHOOK_PORT


@st.cache_resource
def start_cloudflare_tunnels(api_port: int) -> Dict[str, Optional[str]]:
    """
    Automatically opens public HTTPS `*.trycloudflare.com` tunnels for both the iPhone Webhook API
    and the Streamlit Dashboard so the iPhone works over 5G/LTE/any Wi-Fi anywhere in the world!
    """
    urls: Dict[str, Optional[str]] = {"webhook_public": None, "dashboard_public": None}
    try:
        from pycloudflared import try_cloudflare

        tunnel_api = try_cloudflare(port=api_port, verbose=False)
        urls["webhook_public"] = tunnel_api.tunnel.rstrip("/")
    except Exception:
        pass

    try:
        from pycloudflared import try_cloudflare

        tunnel_dash = try_cloudflare(port=8501, verbose=False)
        urls["dashboard_public"] = tunnel_dash.tunnel.rstrip("/")
    except Exception:
        pass

    return urls


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
    api_port = start_iphone_webhook_server()
    cf_urls = start_cloudflare_tunnels(api_port)
    local_ip = get_local_wifi_ip()
    df_test = load_sample_data()
    eval_report = load_eval_report()

    # Check if an SMS was passed directly via Streamlit URL query parameter (?sms=...)
    query_params = st.query_params
    incoming_query_sms = query_params.get("sms", "").strip()
    if incoming_query_sms:
        q_res = pipeline.process_message(incoming_query_sms, preferred_classifier="hybrid_ensemble")
        append_to_iphone_ledger({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_device": "iPhone Shortcut (URL)",
            "raw_sms": q_res["raw_sms"],
            "amount": q_res["amount"],
            "type": q_res["type"],
            "category": q_res["category"],
            "synopsis_category": q_res["synopsis_category"],
            "merchant": q_res["merchant"],
            "beneficiary": q_res["beneficiary"],
            "bank": q_res["bank"],
            "account": q_res["account"],
            "date": q_res["date"],
            "reference": q_res["reference"],
            "vpa": q_res["vpa"],
            "language": q_res["language"],
            "is_code_mixed": q_res["is_code_mixed"],
            "confidence": q_res["confidence"],
        })

    # Public Cloudflare Tunnel URLs (works from anywhere over 5G/LTE!) vs Local Wi-Fi Fallback
    public_api_base = cf_urls.get("webhook_public")
    public_dash_base = cf_urls.get("dashboard_public")

    webhook_post_url = f"{public_api_base}/api/extract" if public_api_base else f"http://{local_ip}:{api_port}/api/extract"
    webhook_get_url = f"{public_api_base}/ingest?sms=" if public_api_base else f"http://{local_ip}:{api_port}/ingest?sms="
    dashboard_mobile_url = public_dash_base if public_dash_base else f"http://{local_ip}:8501"
    local_post_url = f"http://{local_ip}:{api_port}/api/extract"

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
        st.markdown("### ☁️ Public Cloudflare Links")
        if public_api_base:
            st.success("🌐 **Cloudflare Tunnel Active!** Works on 5G / LTE / Any Wi-Fi")
        else:
            st.info("📶 **Local Wi-Fi Mode Active**")
        st.markdown("**1. iPhone Shortcuts POST URL:**")
        st.code(webhook_post_url, language="text")
        st.markdown("**2. iPhone Quick GET URL:**")
        st.code(webhook_get_url, language="text")
        st.markdown("**3. Public Web Dashboard URL:**")
        st.code(dashboard_mobile_url, language="text")

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

    # Top Quick-Copy Server Banner for iPhone Shortcuts (Cloudflare Tunnel + Local Fallback)
    banner_title = (
        "☁️ **Public Cloudflare Tunnel Active (`*.trycloudflare.com`) — Copy Links for iPhone Shortcuts (Works Over 5G / Any Network!)**"
        if public_api_base
        else "📲 **Connect iPhone Shortcuts to this macOS Server (Click to Copy Server Links)**"
    )
    with st.expander(banner_title, expanded=True):
        c_link1, c_link2, c_link3 = st.columns(3)
        with c_link1:
            st.markdown("**1️⃣ Public HTTPS JSON Webhook (POST)**")
            st.caption("Copy into iPhone Shortcuts → `Get Contents of URL` (Works on 5G/LTE anywhere, no same-Wi-Fi needed!):")
            st.code(webhook_post_url, language="text")
        with c_link2:
            st.markdown("**2️⃣ Public One-Line Webhook (GET)**")
            st.caption("Append URL-encoded SMS text directly to this `trycloudflare.com` link:")
            st.code(webhook_get_url, language="text")
        with c_link3:
            st.markdown("**3️⃣ Public Dashboard Link (Anywhere)**")
            st.caption("Open this full macOS dashboard on your iPhone from any mobile network:")
            st.code(dashboard_mobile_url, language="text")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Live SMS Extractor & Explainable AI",
        "📱 iPhone Shortcuts Sync & Live Ledger",
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
        default_sms = incoming_query_sms if incoming_query_sms else PRESET_EXAMPLES[selected_preset]

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
    # TAB 2: IPHONE SHORTCUTS SYNC & LIVE LEDGER
    # =========================================================================
    with tab2:
        st.markdown("### 📱 iPhone Apple Shortcuts Integration & Live Synced Ledger (`trycloudflare.com`)")
        if public_api_base:
            st.success(
                f"☁️ **Cloudflare Public HTTPS Tunnel Active (`{public_api_base}`)!** Your iPhone does **NOT** need to be on the same Wi-Fi as your Mac—it works over 5G, LTE, or any network."
            )
        else:
            st.info(
                f"📶 Your Mac is running a live **FinNLP Webhook Server** on `{local_ip}:{api_port}`."
            )

        col_setup, col_test = st.columns([1.25, 1.0])
        with col_setup:
            st.markdown("#### 🔗 Copyable Server Links for iPhone Shortcuts")
            st.markdown("**Option A — Public HTTPS JSON POST Endpoint (Works Over 5G / Any Network):**")
            st.code(webhook_post_url, language="text")
            st.markdown(
                f"""
                **How to set up in iPhone Shortcuts (takes 30 seconds):**
                1. Open the **Shortcuts** app on your iPhone → tap **Automation** → **New Automation** → **Message**.
                2. Set **Message Contains** to `Rs.` or `INR` or `debited` → choose **Run Immediately**.
                3. Add action **`Get Contents of URL`**:
                   - **URL:** `{webhook_post_url}`
                   - **Method:** `POST`
                   - **Request Body:** `JSON`
                   - Add field: Key = `sms`, Text = `Shortcut Input` (the incoming message content).
                """
            )
            st.markdown("**Option B — Local Same-Wi-Fi Fallback Endpoint:**")
            st.code(local_post_url, language="text")

        with col_test:
            st.markdown("#### 🧪 Simulate / Test an iPhone Shortcut Push")
            sim_sms = st.text_area(
                "Send a test SMS into the live iPhone Ledger:",
                value="HDFC Bank: Rs.649.00 debited from A/c XX4512 on 01-11-2026 to netflix@axis. UPI Ref: 618293041234",
                height=85,
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🚀 Push to Live Ledger", use_container_width=True):
                    res_sim = pipeline.process_message(sim_sms, preferred_classifier=classifier_choice)
                    append_to_iphone_ledger({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_device": "macOS Test / iPhone Sync",
                        "raw_sms": res_sim["raw_sms"],
                        "amount": res_sim["amount"],
                        "type": res_sim["type"],
                        "category": res_sim["category"],
                        "synopsis_category": res_sim["synopsis_category"],
                        "merchant": res_sim["merchant"],
                        "beneficiary": res_sim["beneficiary"],
                        "bank": res_sim["bank"],
                        "account": res_sim["account"],
                        "date": res_sim["date"],
                        "reference": res_sim["reference"],
                        "vpa": res_sim["vpa"],
                        "language": res_sim["language"],
                        "is_code_mixed": res_sim["is_code_mixed"],
                        "confidence": res_sim["confidence"],
                    })
                    st.success("Transaction extracted & saved to live ledger!")
            with col_b2:
                if st.button("🔄 Refresh Ledger", use_container_width=True):
                    st.rerun()

            st.markdown("**Terminal `curl` Command (Test Public Cloudflare Tunnel):**")
            st.code(
                f'curl -X POST {webhook_post_url} \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"sms": "SBI: Rs.350 debited from A/c XX1234 to uber@axis"}}\'',
                language="bash",
            )

        st.markdown("---")
        st.markdown("#### 📋 Live Transactions Synced from iPhone Shortcuts")
        iphone_records = load_iphone_ledger()
        if iphone_records:
            df_iphone = pd.DataFrame(iphone_records)
            ic1, ic2, ic3 = st.columns(3)
            total_ip_spend = df_iphone[df_iphone["type"] == "debit"]["amount"].fillna(0).sum()
            ic1.metric("Synced Transactions", f"{len(df_iphone)}")
            ic2.metric("Total Synced Spend (Debits)", f"₹{total_ip_spend:,.2f}")
            ic3.metric("Latest Sync Timestamp", str(df_iphone.iloc[0].get("timestamp", "Just now")))

            st.dataframe(df_iphone, use_container_width=True, height=280)
            if st.button("🗑️ Clear Synced iPhone Ledger"):
                if IPHONE_LEDGER_PATH.exists():
                    IPHONE_LEDGER_PATH.unlink()
                st.rerun()
        else:
            st.info(
                "No iPhone transactions synced yet. Copy the webhook URL above into your iPhone **Shortcuts** app or click **🚀 Push to Live Ledger** to test!"
            )

    # =========================================================================
    # TAB 3: PERSONAL EXPENSE TRACKER & BATCH ANALYZER
    # =========================================================================
    with tab3:
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
    # TAB 4: MULTILINGUAL & CODE-MIXED EXPLORER
    # =========================================================================
    with tab4:
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
    # TAB 5: MODEL BENCHMARKS & EVALUATION REPORT
    # =========================================================================
    with tab5:
        st.markdown("### 📈 Experimental Evaluation & Model Comparison")
        if eval_report:
            cat_key = "categorization" if "categorization" in eval_report else "expense_categorization"
            if cat_key in eval_report:
                st.markdown("#### 1. Expense Categorization Model Comparison")
                models_tbl = pd.DataFrame.from_dict(eval_report[cat_key]["overall_models"], orient="index")
                models_tbl = models_tbl.reset_index().rename(columns={"index": "Model Architecture"})
                for col in ["accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"]:
                    if col in models_tbl.columns:
                        models_tbl[col] = (models_tbl[col] * 100).round(2).astype(str) + "%"
                st.table(models_tbl)

            if "entity_extraction" in eval_report:
                st.markdown("#### 2. Financial Entity Extraction (NER + Regex) Performance")
                ext_tbl = pd.DataFrame.from_dict(eval_report["entity_extraction"], orient="index")
                ext_tbl = ext_tbl.reset_index().rename(columns={"index": "Entity Field"})
                for col in ["precision", "recall", "f1_score"]:
                    if col in ext_tbl.columns:
                        ext_tbl[col] = (ext_tbl[col] * 100).round(2).astype(str) + "%"
                st.table(ext_tbl)

            st.markdown("#### 3. Visual Performance Charts")
            c1, c2 = st.columns(2)
            with c1:
                for fname in ["fig_model_comparison.png", "model_comparison.png"]:
                    if (OUTPUTS_DIR / fname).exists():
                        st.image(str(OUTPUTS_DIR / fname), caption="Model Comparison on FinEE Test Set")
                        break
                for fname in ["fig_multilingual_performance.png", "multilingual_performance.png"]:
                    if (OUTPUTS_DIR / fname).exists():
                        st.image(str(OUTPUTS_DIR / fname), caption="Multilingual & Code-Mixed Accuracy Breakdown")
                        break
            with c2:
                for fname in ["fig_entity_extraction.png", "entity_extraction_f1.png"]:
                    if (OUTPUTS_DIR / fname).exists():
                        st.image(str(OUTPUTS_DIR / fname), caption="Entity Extraction Precision, Recall & F1")
                        break
                for fname in ["fig_confusion_matrix.png", "confusion_matrix.png"]:
                    if (OUTPUTS_DIR / fname).exists():
                        st.image(str(OUTPUTS_DIR / fname), caption="Normalized Category Confusion Matrix")
                        break
        else:
            st.warning("Run `python train_and_evaluate.py` first to generate evaluation metrics and plots.")


if __name__ == "__main__":
    main()
