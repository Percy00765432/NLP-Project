"""
Master Training & Evaluation Pipeline for the Robust Financial NLP Framework.

Usage:
    python train_and_evaluate.py [--train-size 16000] [--eval-size 2500] [--train-transformer]
                                 [--transformer-model google/muril-base-cased]
"""

import argparse
import json
import time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

from src.config import DATA_DIR, MODELS_DIR, OUTPUTS_DIR, SUPPORTED_LANGUAGES
from src.data_loader import load_or_build_dataset
from src.categorizer import (
    ClassicalMLCategorizer,
    MultilingualTransformerCategorizer,
    HybridTransactionPipeline,
)
from src.evaluator import evaluate_entity_extraction, evaluate_categorization_models


def generate_evaluation_charts(eval_report: Dict, extraction_report: Dict) -> None:
    """Generates publication-quality evaluation plots in `outputs/`."""
    sns.set_theme(style="whitegrid", palette="deep")

    # 1. Model Comparison Bar Chart (Accuracy & Macro F1)
    models_dict = eval_report["overall_models"]
    model_names = list(models_dict.keys())
    accs = [models_dict[m]["accuracy"] * 100 for m in model_names]
    f1s = [models_dict[m]["macro_f1"] * 100 for m in model_names]

    x = np.arange(len(model_names))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11, 5.5))
    rects1 = ax.bar(x - width / 2, accs, width, label="Accuracy (%)", color="#2563eb")
    rects2 = ax.bar(x + width / 2, f1s, width, label="Macro F1-Score (%)", color="#10b981")

    ax.set_ylabel("Score (%)", fontsize=12, fontweight="bold")
    ax.set_title("Expense Categorization Performance Across Models (FinEE + Multilingual Test Set)", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=18, ha="right", fontsize=10)
    ax.set_ylim(0, 108)
    ax.legend(loc="lower right", frameon=True)

    for rect in rects1 + rects2:
        h = rect.get_height()
        ax.annotate(
            f"{h:.1f}%",
            xy=(rect.get_x() + rect.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "model_comparison.png", dpi=200)
    plt.close()

    # 2. Entity Extraction Performance Chart (Precision, Recall, F1 per Entity)
    ent_fields = [k for k in extraction_report.keys() if k != "macro_average"]
    ent_f1 = [extraction_report[k]["f1_score"] * 100 for k in ent_fields]
    ent_prec = [extraction_report[k]["precision"] * 100 for k in ent_fields]
    ent_rec = [extraction_report[k]["recall"] * 100 for k in ent_fields]

    x_e = np.arange(len(ent_fields))
    w_e = 0.26
    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.bar(x_e - w_e, ent_prec, w_e, label="Precision (%)", color="#3b82f6")
    ax.bar(x_e, ent_rec, w_e, label="Recall (%)", color="#f59e0b")
    ax.bar(x_e + w_e, ent_f1, w_e, label="F1-Score (%)", color="#8b5cf6")

    ax.set_ylabel("Score (%)", fontsize=12, fontweight="bold")
    ax.set_title("Financial Entity Extraction (NER + Pattern Recognition) Performance by Field", fontsize=13, fontweight="bold")
    ax.set_xticks(x_e)
    ax.set_xticklabels([f.upper() for f in ent_fields], fontsize=10, fontweight="bold")
    ax.set_ylim(0, 108)
    ax.legend(loc="lower right", frameon=True)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "entity_extraction_f1.png", dpi=200)
    plt.close()

    # 3. Confusion Matrix Heatmap
    cm_data = eval_report["confusion_matrix"]
    labels = cm_data["labels"]
    mat = np.array(cm_data["matrix"], dtype=float)
    # Normalize by row (true class) for percentages
    row_sums = mat.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    mat_norm = (mat / row_sums) * 100

    fig, ax = plt.subplots(figsize=(11, 8.5))
    sns.heatmap(
        mat_norm,
        annot=True,
        fmt=".1f",
        cmap="Blues",
        xticklabels=[l.capitalize() for l in labels],
        yticklabels=[l.capitalize() for l in labels],
        cbar_kws={"label": "Row-Normalized Accuracy (%)"},
        ax=ax,
    )
    ax.set_xlabel("Predicted Expense Category", fontsize=12, fontweight="bold")
    ax.set_ylabel("True Expense Category", fontsize=12, fontweight="bold")
    ax.set_title("Normalized Confusion Matrix (%) — Hybrid NLP Framework", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "confusion_matrix.png", dpi=200)
    plt.close()

    # 4. Multilingual & Code-Mixed Accuracy Breakdown
    lang_data = eval_report["language_breakdown"]
    lang_keys = sorted(lang_data.keys(), key=lambda k: -lang_data[k]["samples"])
    lang_labels = [f"{lang_data[k]['language_name']}\n(n={lang_data[k]['samples']})" for k in lang_keys]
    lang_accs = [lang_data[k]["accuracy"] * 100 for k in lang_keys]
    lang_f1s = [lang_data[k]["macro_f1"] * 100 for k in lang_keys]

    x_l = np.arange(len(lang_keys))
    fig, ax = plt.subplots(figsize=(10.5, 5))
    b1 = ax.bar(x_l - 0.18, lang_accs, 0.35, label="Accuracy (%)", color="#0ea5e9")
    b2 = ax.bar(x_l + 0.18, lang_f1s, 0.35, label="Macro F1 (%)", color="#14b8a6")
    ax.set_ylabel("Score (%)", fontsize=12, fontweight="bold")
    ax.set_title("Multilingual & Code-Mixed Performance Breakdown Across Indian Languages", fontsize=13, fontweight="bold")
    ax.set_xticks(x_l)
    ax.set_xticklabels(lang_labels, fontsize=9.5)
    ax.set_ylim(0, 108)
    ax.legend(loc="lower right", frameon=True)
    for rect in list(b1) + list(b2):
        h = rect.get_height()
        ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8.5)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "multilingual_performance.png", dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the Financial NLP Framework.")
    parser.add_argument("--train-size", type=int, default=16000, help="Number of FinEE training samples to fetch")
    parser.add_argument("--eval-size", type=int, default=2500, help="Number of FinEE validation/test samples to fetch")
    parser.add_argument("--force-download", action="store_true", help="Re-stream dataset from Hugging Face")
    parser.add_argument("--train-transformer", action="store_true", help="Fine-tune a Hugging Face multilingual transformer")
    parser.add_argument(
        "--transformer-model",
        type=str,
        default="google/muril-base-cased",
        help="HF Transformer model ID (e.g., google/muril-base-cased, xlm-roberta-base, distilbert-base-multilingual-cased)",
    )
    parser.add_argument("--transformer-samples", type=int, default=4500, help="Subsample size for rapid local transformer fine-tuning")
    args = parser.parse_args()

    t0 = time.time()
    print("=" * 80)
    print("ROBUST NLP FRAMEWORK FOR AUTOMATED FINANCIAL TRANSACTION EXTRACTION & CATEGORIZATION")
    print("=" * 80)

    # Step 1: Load / Stream FinEE Dataset + Code-Mixed & Education Augmentation
    df_train, df_valid, df_test = load_or_build_dataset(
        max_train_samples=args.train_size,
        max_eval_samples=args.eval_size,
        force_download=args.force_download,
    )

    print(f"\nDataset Summary:")
    print(f"  Train split : {len(df_train):,} messages")
    print(f"  Valid split : {len(df_valid):,} messages")
    print(f"  Test split  : {len(df_test):,} messages")
    print(f"  Categories  : {sorted(df_train['category'].unique().tolist())}")
    print(f"  Languages   : {df_train['language'].value_counts().to_dict()}")

    # Step 2: Train Classical & Subword ML Categorizers (SVM, Logistic Regression, LightGBM)
    print("\n" + "-" * 80)
    print("STEP 2: Training Classical & Ensemble ML Categorizers (Word + Char N-Gram TF-IDF)")
    print("-" * 80)
    classical_clf = ClassicalMLCategorizer()
    classical_clf.fit(
        df_train["raw_sms"].astype(str).tolist(),
        df_train["category"].astype(str).tolist(),
    )
    saved_pkl = classical_clf.save()
    print(f"Saved classical models to: {saved_pkl}")

    # Step 3: Optional Multilingual Transformer Fine-Tuning (MuRIL / XLM-R / mDistilBERT)
    transformer_clf = None
    if args.train_transformer:
        print("\n" + "-" * 80)
        print(f"STEP 3: Fine-Tuning Multilingual Transformer ({args.transformer_model})")
        print("-" * 80)
        try:
            df_tr_sub = df_train.sample(n=min(args.transformer_samples, len(df_train)), random_state=42)
            df_va_sub = df_valid.sample(n=min(1000, len(df_valid)), random_state=42)
            transformer_clf = MultilingualTransformerCategorizer(args.transformer_model)
            transformer_clf.train_and_save(
                train_texts=df_tr_sub["normalized_text"].astype(str).tolist(),
                train_labels=df_tr_sub["category"].astype(str).tolist(),
                val_texts=df_va_sub["normalized_text"].astype(str).tolist(),
                val_labels=df_va_sub["category"].astype(str).tolist(),
                epochs=2,
                batch_size=32,
            )
        except Exception as e:
            print(f"Note: Transformer fine-tuning skipped or encountered error: {e}")
            transformer_clf = None
    elif (MODELS_DIR / "multilingual_transformer").exists():
        transformer_clf = MultilingualTransformerCategorizer.load()

    # Step 4: Evaluate Financial Entity Extraction (NER + Regex)
    print("\n" + "-" * 80)
    print("STEP 4: Evaluating Financial Entity Extraction on Test Set")
    print("-" * 80)
    extraction_metrics = evaluate_entity_extraction(df_test)
    for field, m in extraction_metrics.items():
        print(
            f"  {field.upper():15s} | Precision: {m['precision']*100:6.2f}% | Recall: {m['recall']*100:6.2f}% | F1: {m['f1_score']*100:6.2f}% (n={m['support']})"
        )

    # Step 5: Evaluate Expense Categorization Models & Language Breakdown
    print("\n" + "-" * 80)
    print("STEP 5: Evaluating Expense Categorization Models on Test Set")
    print("-" * 80)
    categorization_metrics = evaluate_categorization_models(
        df_test=df_test,
        classical_model=classical_clf,
        transformer_model=transformer_clf,
    )

    for model_name, m in categorization_metrics["overall_models"].items():
        print(
            f"  {model_name:42s} | Acc: {m['accuracy']*100:6.2f}% | Macro F1: {m['macro_f1']*100:6.2f}% | Weighted F1: {m['weighted_f1']*100:6.2f}%"
        )

    print("\nLanguage & Code-Mixed Breakdown (Hybrid Ensemble Framework):")
    for lang_code, lm in categorization_metrics["language_breakdown"].items():
        print(
            f"  [{lang_code:8s}] {lm['language_name']:42s} | Acc: {lm['accuracy']*100:6.2f}% | Macro F1: {lm['macro_f1']*100:6.2f}% (n={lm['samples']})"
        )

    # Save full JSON report and generate visual charts
    full_report = {
        "dataset_summary": {
            "train_samples": int(len(df_train)),
            "valid_samples": int(len(df_valid)),
            "test_samples": int(len(df_test)),
            "languages": df_train["language"].value_counts().to_dict(),
            "categories": df_train["category"].value_counts().to_dict(),
        },
        "entity_extraction": extraction_metrics,
        "expense_categorization": categorization_metrics,
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    report_path = OUTPUTS_DIR / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)

    generate_evaluation_charts(categorization_metrics, extraction_metrics)
    print(f"\nSaved full evaluation report to {report_path}")
    print(f"Saved evaluation charts to {OUTPUTS_DIR}")
    print(f"Completed in {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()
