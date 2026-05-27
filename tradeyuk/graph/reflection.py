# tradeyuk/graph/reflection.py

from typing import Any


class Reflector:
    """Handles reflection on trading decisions."""

    def __init__(self, quick_thinking_llm: Any):
        """Initialize the reflector with an LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.log_reflection_prompt = self._get_log_reflection_prompt()

    def _get_log_reflection_prompt(self) -> str:
        """Prompt ringkas untuk reflect_on_final_decision (entri log Fase B).

        Menghasilkan 2-4 kalimat prosa biasa — cukup ringkas untuk disuntikkan ulang
        ke dalam prompt agen masa depan tanpa membengkakkan jendela konteks.
        """
        return (
            "Anda adalah analis trading yang meninjau keputusan Anda sendiri di masa lalu sekarang setelah hasilnya diketahui.\n"
            "Tulis tepat 2-4 kalimat prosa biasa (tanpa poin, tanpa tajuk, tanpa markdown).\n\n"
            "Cakup secara berurutan:\n"
            "1. Apakah panggilan arah sudah benar? (sebutkan angka alpha)\n"
            "2. Bagian mana dari tesis investasi yang bertahan atau gagal?\n"
            "3. Satu pelajaran konkret untuk diterapkan pada analisis serupa berikutnya.\n\n"
            "Bersikaplah spesifik dan ringkas. Output Anda akan disimpan kata demi kata dalam log keputusan "
            "dan dibaca ulang oleh analis masa depan, jadi setiap kata harus bermakna."
        )

    def reflect_on_final_decision(
        self,
        final_decision: str,
        raw_return: float,
        alpha_return: float,
        benchmark_name: str = "SPY",
    ) -> str:
        """Panggilan refleksi tunggal pada keputusan trading final dengan konteks hasil.

        Digunakan oleh refleksi tertunda Fase B. final_trade_decision sudah
        mensintesis semua wawasan analis, jadi tidak diperlukan konteks pasar terpisah.
        ``benchmark_name`` adalah label yang digunakan untuk baris alpha (mis. ``"SPY"``
        untuk ticker AS, ``"^N225"`` untuk listing ``.T``); default ke SPY untuk
        pemanggil yang belum diperbarui untuk meneruskan benchmark.
        """
        messages = [
            ("system", self.log_reflection_prompt),
            (
                "human",
                (
                    f"Imbal hasil mentah: {raw_return:+.1%}\n"
                    f"Alpha vs {benchmark_name}: {alpha_return:+.1%}\n\n"
                    f"Keputusan Final:\n{final_decision}"
                ),
            ),
        ]
        return self.quick_thinking_llm.invoke(messages).content
