"""Pydantic schemas used by agents that produce structured output.

The framework's primary artifact is still prose: each agent's natural-language
reasoning is what users read in the saved markdown reports and what the
downstream agents read as context.  Structured output is layered onto the
three decision-making agents (Research Manager, Trader, Portfolio Manager)
so that:

- Their outputs follow consistent section headers across runs and providers
- Each provider's native structured-output mode is used (json_schema for
  OpenAI/xAI, response_schema for Gemini, tool-use for Anthropic)
- Schema field descriptions become the model's output instructions, freeing
  the prompt body to focus on context and the rating-scale guidance
- A render helper turns the parsed Pydantic instance back into the same
  markdown shape the rest of the system already consumes, so display,
  memory log, and saved reports keep working unchanged
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared rating types
# ---------------------------------------------------------------------------


class PortfolioRating(str, Enum):
    """Peringkat 5-tingkat yang digunakan oleh Manajer Riset dan Manajer Portofolio."""

    BUY = "Beli"
    OVERWEIGHT = "Overweight"
    HOLD = "Tahan"
    UNDERWEIGHT = "Underweight"
    SELL = "Jual"


class TraderAction(str, Enum):
    """Arah transaksi 3-tingkat yang digunakan oleh Trader.

    Tugas Trader adalah menerjemahkan rencana investasi Manajer Riset
    menjadi proposal transaksi konkret: apakah meja harus mengeksekusi Beli,
    Jual, atau diam di Tahan pada putaran ini. Penentuan ukuran posisi dan
    panggilan nuansa Overweight / Underweight terjadi nanti di Manajer Portofolio.
    """

    BUY = "Beli"
    HOLD = "Tahan"
    SELL = "Jual"


# ---------------------------------------------------------------------------
# Research Manager
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """Rencana investasi terstruktur yang dihasilkan oleh Manajer Riset.

    Serah terima ke Trader: rekomendasi menentukan pandangan arah,
    rasional menangkap sisi mana dari perdebatan bull/bear yang membawa
    argumen, dan langkah strategis menerjemahkannya ke dalam instruksi
    konkret yang dapat dieksekusi trader.
    """

    recommendation: PortfolioRating = Field(
        description=(
            "Rekomendasi investasi. Tepat satu dari Beli / Overweight / "
            "Tahan / Underweight / Jual. Cadangkan Tahan untuk situasi di mana "
            "bukti di kedua sisi benar-benar seimbang; jika tidak, berkomitmenlah pada "
            "sisi dengan argumen yang lebih kuat."
        ),
    )
    rationale: str = Field(
        description=(
            "Ringkasan percakapan dari poin-poin kunci dari kedua sisi "
            "perdebatan, diakhiri dengan argumen mana yang mengarah pada rekomendasi. "
            "Bicaralah secara alami, seolah-olah kepada rekan tim."
        ),
    )
    strategic_actions: str = Field(
        description=(
            "Langkah-langkah konkret bagi trader untuk mengimplementasikan rekomendasi, "
            "termasuk panduan penentuan ukuran posisi yang konsisten dengan peringkat."
        ),
    )


def render_research_plan(plan: ResearchPlan) -> str:
    """Render ResearchPlan ke markdown untuk penyimpanan dan konteks prompt trader."""
    return "\n".join([
        f"**Rekomendasi**: {plan.recommendation.value}",
        "",
        f"**Rasional**: {plan.rationale}",
        "",
        f"**Langkah Strategis**: {plan.strategic_actions}",
    ])


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------


class TraderProposal(BaseModel):
    """Proposal transaksi terstruktur yang dihasilkan oleh Trader.

    Trader membaca rencana investasi Manajer Riset dan laporan analis,
    lalu mengubahnya menjadi transaksi konkret: aksi apa yang diambil,
    alasan yang membenarkannya, dan level praktis untuk
    masuk, stop-loss, dan penentuan ukuran.
    """

    action: TraderAction = Field(
        description="Arah transaksi. Tepat satu dari Beli / Tahan / Jual.",
    )
    reasoning: str = Field(
        description=(
            "Alasan untuk aksi ini, berlabuh pada laporan analis dan "
            "rencana riset. Dua hingga empat kalimat."
        ),
    )
    entry_price: Optional[float] = Field(
        default=None,
        description="Target harga masuk opsional dalam mata uang kuotasi instrumen.",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description="Harga stop-loss opsional dalam mata uang kuotasi instrumen.",
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="Panduan penentuan ukuran opsional, mis. '5% dari portofolio'.",
    )


def render_trader_proposal(proposal: TraderProposal) -> str:
    """Render TraderProposal ke markdown.

    Baris ``PROPOSAL TRANSAKSI FINAL: **BELI/TAHAN/JUAL**`` di akhir
    dipertahankan untuk kompatibilitas mundur dengan teks sinyal berhenti analis
    dan kode eksternal apa pun yang melakukan grep untuknya.
    """
    parts = [
        f"**Aksi**: {proposal.action.value}",
        "",
        f"**Alasan**: {proposal.reasoning}",
    ]
    if proposal.entry_price is not None:
        parts.extend(["", f"**Harga Masuk**: {proposal.entry_price}"])
    if proposal.stop_loss is not None:
        parts.extend(["", f"**Stop Loss**: {proposal.stop_loss}"])
    if proposal.position_sizing:
        parts.extend(["", f"**Ukuran Posisi**: {proposal.position_sizing}"])
    parts.extend([
        "",
        f"PROPOSAL TRANSAKSI FINAL: **{proposal.action.value.upper()}**",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Portfolio Manager
# ---------------------------------------------------------------------------


class PortfolioDecision(BaseModel):
    """Output terstruktur yang dihasilkan oleh Manajer Portofolio.

    Model mengisi setiap bidang sebagai bagian dari panggilan LLM utamanya; tidak diperlukan
    langkah ekstraksi terpisah. Deskripsi bidang berfungsi ganda sebagai instruksi
    output model, sehingga badan prompt hanya perlu menyampaikan konteks dan
    panduan skala peringkat.
    """

    rating: PortfolioRating = Field(
        description=(
            "Peringkat posisi final. Tepat satu dari Beli / Overweight / Tahan / "
            "Underweight / Jual, dipilih berdasarkan perdebatan analis."
        ),
    )
    executive_summary: str = Field(
        description=(
            "Rencana aksi ringkas yang mencakup strategi masuk, penentuan ukuran posisi, "
            "level risiko kunci, dan horison waktu. Dua hingga empat kalimat."
        ),
    )
    investment_thesis: str = Field(
        description=(
            "Alasan terperinci yang berlabuh pada bukti spesifik dari perdebatan "
            "analis. Jika pelajaran sebelumnya dirujuk dalam konteks prompt, "
            "gabungkanlah; jika tidak, andalkan semata-mata pada analisis saat ini."
        ),
    )
    price_target: Optional[float] = Field(
        default=None,
        description="Target harga opsional dalam mata uang kuotasi instrumen.",
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="Periode penahanan yang direkomendasikan opsional, mis. '3-6 bulan'.",
    )


def render_pm_decision(decision: PortfolioDecision) -> str:
    """Render PortfolioDecision kembali ke bentuk markdown yang diharapkan oleh sistem lainnya.

    Log memori, tampilan CLI, dan file laporan yang disimpan semuanya membaca markdown ini,
    jadi output yang dirender mempertahankan tajuk bagian yang persis (``**Peringkat**``,
    ``**Ringkasan Eksekutif**``, ``**Tesis Investasi**``) yang sudah ditangani
    oleh parser hilir dan penulis laporan.
    """
    parts = [
        f"**Peringkat**: {decision.rating.value}",
        "",
        f"**Ringkasan Eksekutif**: {decision.executive_summary}",
        "",
        f"**Tesis Investasi**: {decision.investment_thesis}",
    ]
    if decision.price_target is not None:
        parts.extend(["", f"**Target Harga**: {decision.price_target}"])
    if decision.time_horizon:
        parts.extend(["", f"**Horison Waktu**: {decision.time_horizon}"])
    return "\n".join(parts)
