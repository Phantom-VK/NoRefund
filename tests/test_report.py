"""Tests for core/report: the ReportModel -> HTML string builder and the
ReportModel -> PDF bytes builder."""

from datetime import datetime

from norefund.core.architectures import ModelArchitecture
from norefund.core.compare import CompareReport, ModelComparison
from norefund.core.hardware_registry import HardwareTarget
from norefund.core.models_registry import ModelInfo
from norefund.core.portfolio import PortfolioProjection
from norefund.core.report.html import render_html
from norefund.core.report.model import ReportModel
from norefund.core.report.pdf import render_pdf
from norefund.core.selfhost import evaluate_fit
from norefund.core.service import AnalysisResult

_MODEL = ModelInfo(
    id="test:model",
    display_name="Test Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=128_000,
    input_price_per_million=1.0,
    output_price_per_million=2.0,
)

_ARCH = ModelArchitecture(
    id="test:arch",
    display_name="Test Arch 8B",
    family="Test",
    vendor="Test",
    total_params=8_000_000_000,
    active_params=8_000_000_000,
    n_layers=32,
    n_attention_heads=32,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=4096,
    max_context_length=131072,
    attention_type="gqa",
)

_HW = HardwareTarget(
    id="test:hw",
    display_name="Test GPU 80GB",
    category="datacenter_gpu",
    vendor="Test",
    accelerator="Test Accelerator",
    device_count=1,
    memory_gib_per_device=80.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_ZERO_VRAM_HW = HardwareTarget(
    id="test:zero",
    display_name="Zero VRAM",
    category="datacenter_gpu",
    vendor="Test",
    accelerator="None",
    device_count=1,
    memory_gib_per_device=0.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_GENERATED_AT = datetime(2026, 8, 15, 12, 0)


def _analysis_results() -> list[AnalysisResult]:
    return [
        AnalysisResult(
            file_path="deck.pptx",
            model_id=_MODEL.id,
            char_count=10_000,
            word_count=2_000,
            token_count=3_000,
            context_window=128_000,
            context_usage_pct=2.34,
            fits_in_context=True,
            min_chunks_needed=1,
            estimated_input_cost=0.003,
        ),
        AnalysisResult(
            file_path="broken.pdf",
            model_id=_MODEL.id,
            char_count=0,
            word_count=0,
            token_count=0,
            context_window=128_000,
            context_usage_pct=None,
            fits_in_context=False,
            min_chunks_needed=0,
            estimated_input_cost=0.0,
            error="Could not parse file",
        ),
    ]


def _compare_report() -> CompareReport:
    return CompareReport(
        source_label="1 file",
        results=[
            ModelComparison(
                model=_MODEL,
                token_count=3_000,
                context_usage_pct=2.34,
                fits_in_context=True,
                min_chunks_needed=1,
                output_tokens=500,
                input_cost=0.003,
                output_cost=0.001,
                total_cost=0.004,
                tokenizer_is_approximate=False,
            )
        ],
    )


def _portfolio() -> list[PortfolioProjection]:
    return [
        PortfolioProjection(
            model=_MODEL,
            corpus_tokens=3_000,
            fits_in_context=True,
            cost_per_run=0.004,
            monthly_cost=0.12,
            annual_cost=1.44,
        )
    ]


def _empty_report() -> ReportModel:
    return ReportModel(title="Empty Report", generated_at=_GENERATED_AT)


def _full_report() -> ReportModel:
    fit = evaluate_fit(_ARCH, _HW, "q4_k_m", 8192)
    return ReportModel(
        title="Full Report",
        generated_at=_GENERATED_AT,
        analysis=_analysis_results(),
        comparison=_compare_report(),
        fit=fit,
        fit_architecture_name=_ARCH.display_name,
        fit_hardware_name=_HW.display_name,
        fit_quantization_name="Q4_K_M",
        fit_kv_cache_name="FP16",
        portfolio=_portfolio(),
        portfolio_frequency_label="100 runs/daily",
    )


# ----------------------------------------------------------------------
# ReportModel
# ----------------------------------------------------------------------


def test_report_model_has_content_false_when_empty():
    assert _empty_report().has_content is False


def test_report_model_has_content_true_with_any_section():
    report = ReportModel(
        title="t", generated_at=_GENERATED_AT, analysis=_analysis_results()
    )
    assert report.has_content is True


# ----------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------


def test_render_html_empty_report_is_valid_shell():
    html = render_html(_empty_report())
    assert html.startswith("<!doctype html>")
    assert "Empty Report" in html
    assert "No data to report." in html


def test_render_html_includes_all_sections():
    html = render_html(_full_report())
    assert "Analysis" in html
    assert "deck.pptx" in html
    assert "Could not parse file" in html
    assert "Comparison" in html
    assert "Test Model" in html
    assert "Fit Check" in html
    assert "Test Arch 8B" in html
    assert "Test GPU 80GB" in html
    assert "Portfolio projection" in html
    assert "100 runs/daily" in html


def test_render_html_escapes_untrusted_text():
    report = ReportModel(
        title="<script>alert(1)</script>", generated_at=_GENERATED_AT
    )
    html = render_html(report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_html_renders_fit_error_without_estimate():
    fit = evaluate_fit(_ARCH, _ZERO_VRAM_HW, "q4_k_m", 8192)
    # Zero-VRAM hardware still produces a usable (zero) estimate rather than
    # an error -- use an actually-invalid input to hit the error branch.
    bad_fit = evaluate_fit(_ARCH, _HW, "not_a_real_quant", 8192)
    assert bad_fit.error is not None
    report = ReportModel(title="Fit Error", generated_at=_GENERATED_AT, fit=bad_fit)
    html = render_html(report)
    assert "Unknown quantization level" in html
    # sanity: the zero-VRAM fixture is still well-formed (no error)
    assert fit.error is None


# ----------------------------------------------------------------------
# PDF
# ----------------------------------------------------------------------


def test_render_pdf_returns_pdf_bytes():
    pdf_bytes = render_pdf(_empty_report())
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0


def test_render_pdf_full_report_returns_nonempty_pdf_bytes():
    pdf_bytes = render_pdf(_full_report())
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_render_pdf_handles_fit_error_without_raising():
    bad_fit = evaluate_fit(_ARCH, _HW, "not_a_real_quant", 8192)
    report = ReportModel(title="Fit Error", generated_at=_GENERATED_AT, fit=bad_fit)
    pdf_bytes = render_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
