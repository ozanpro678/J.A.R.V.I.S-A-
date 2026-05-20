"""
PDF tabanli odevleri Gemini ile cozer ve daha sonra soru-cevap yapar.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors, types

from app_config import get_app_config_value


BASE_DIR = Path(__file__).resolve().parents[1]
HOMEWORK_DIR = BASE_DIR / "memory" / "homework"
ACTIVE_HOMEWORK_PATH = HOMEWORK_DIR / "active_homework.json"

HOMEWORK_MODELS = (
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-lite",
)
MAX_INLINE_PDF_BYTES = 24 * 1024 * 1024


def _api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "").strip()


def _extract_response_text(response) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if text:
        return text

    candidates = getattr(response, "candidates", None) or []
    chunks: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = str(getattr(part, "text", "") or "").strip()
            if part_text:
                chunks.append(part_text)
    return "\n".join(chunks).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)

    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(clean[start : end + 1])
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Gemini JSON formatinda cozum dondurmedi.")


def _is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, (errors.ServerError, TimeoutError)):
        return True
    message = str(exc or "").lower()
    markers = (
        "503",
        "429",
        "deadline",
        "timed out",
        "timeout",
        "unavailable",
        "service unavailable",
        "internal error",
        "overloaded",
        "resource exhausted",
        "try again later",
        "backend error",
    )
    return any(marker in message for marker in markers)


def _friendly_error(exc: Exception) -> str:
    message = str(exc or "")
    lower = message.lower()
    if any(marker in lower for marker in ("quota", "rate limit", "resource exhausted", "billing")):
        return "Gemini kota veya hiz limitine takildi. Biraz bekleyip tekrar dene ya da API planini kontrol et."
    if _is_transient_error(exc):
        return "Gemini su anda yogun veya gecici olarak ulasilamiyor. Biraz sonra tekrar dene."
    return f"Odev analizi tamamlanamadi: {message}"


def _save_homework(payload: dict[str, Any]) -> None:
    HOMEWORK_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_HOMEWORK_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_active_homework() -> dict[str, Any] | None:
    try:
        data = json.loads(ACTIVE_HOMEWORK_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _build_solve_prompt(file_name: str) -> str:
    return (
        "Sen JARVIS icin odev cozme modulusun. Kullanici bir PDF odev dosyasi yukledi.\n"
        "Gorevin PDF'teki tum test, klasik, acik uclu, bosluk doldurma, dogru-yanlis ve benzeri "
        "sorulari tespit edip cozmek.\n\n"
        "Kurallar:\n"
        "- Yaniti Turkce hazirla.\n"
        "- Uydurma yapma; okunmayan veya eksik soru varsa bunu notlarda belirt.\n"
        "- Test sorularinda sik harfini ve sik metnini yaz.\n"
        "- Acik uclu sorularda kisa ama yeterli bir cevap ve gerekce ver.\n"
        "- Cikti SADECE gecerli JSON olsun; markdown, aciklama veya kod blogu ekleme.\n\n"
        "JSON semasi:\n"
        "{\n"
        '  "title": "odev basligi veya dosya adi",\n'
        '  "source_file": "' + file_name.replace('"', "'") + '",\n'
        '  "summary": "odevin kisa ozeti",\n'
        '  "questions": [\n'
        "    {\n"
        '      "id": "Test 1 - 1" veya "1",\n'
        '      "section": "Test 1 / Bolum adi / Bos",\n'
        '      "question": "soru metni",\n'
        '      "answer": "dogrudan cevap",\n'
        '      "explanation": "kisa cozum veya gerekce",\n'
        '      "confidence": "high|medium|low"\n'
        "    }\n"
        "  ],\n"
        '  "notes": ["okunamayan yerler veya genel notlar"]\n'
        "}\n"
    )


def solve_homework_pdf(file_path: str) -> str:
    path = Path(file_path).expanduser()
    if not path.exists():
        return "PDF dosyasi bulunamadi. Lutfen odev menusunden tekrar PDF sec."
    if path.suffix.lower() != ".pdf":
        return "Sadece .pdf uzantili odev dosyalari destekleniyor."
    if path.stat().st_size <= 0:
        return "Secilen PDF bos gorunuyor."
    if path.stat().st_size > MAX_INLINE_PDF_BYTES:
        return "PDF cok buyuk. Lutfen 24 MB altinda bir PDF yukle."

    api_key = _api_key()
    if not api_key:
        return "Gemini API anahtari eksik oldugu icin odev cozulmedi."

    client = genai.Client(api_key=api_key)
    pdf_part = types.Part.from_bytes(
        data=path.read_bytes(),
        mime_type="application/pdf",
    )
    prompt = _build_solve_prompt(path.name)
    last_error: Exception | None = None

    for model_name in HOMEWORK_MODELS:
        for attempt, delay in enumerate((0.8, 1.8, 3.0), start=1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Part.from_text(text=prompt), pdf_part],
                    config=types.GenerateContentConfig(
                        temperature=0.15,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = _extract_response_text(response)
                solved = _extract_json_object(raw_text)
                questions = solved.get("questions", [])
                if not isinstance(questions, list):
                    solved["questions"] = []

                payload = {
                    "status": "ready",
                    "source_path": str(path),
                    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "solution": solved,
                    "raw_solution": raw_text,
                }
                _save_homework(payload)
                count = len(solved.get("questions", []) or [])
                return f"Ödevleriniz hazır. {count} soru çözüldü; artık soruları tek tek sorabilirsin."
            except Exception as exc:
                last_error = exc
                if attempt < 3 and _is_transient_error(exc):
                    time.sleep(delay)
                    continue
                if _is_transient_error(exc):
                    break
                return _friendly_error(exc)

    assert last_error is not None
    return _friendly_error(last_error)


def _homework_context(data: dict[str, Any]) -> str:
    solution = data.get("solution", {})
    if isinstance(solution, dict):
        return json.dumps(solution, ensure_ascii=False, indent=2)
    raw = str(data.get("raw_solution", "") or "").strip()
    return raw


def answer_homework_question(query: str) -> str:
    data = load_active_homework()
    if not data or data.get("status") != "ready":
        return "Hazir bir odev cozumu yok. Once 'JARVIS odev menumu ac' deyip PDF yukle."

    api_key = _api_key()
    if not api_key:
        return "Gemini API anahtari eksik oldugu icin odev cevabi verilemiyor."

    context = _homework_context(data)
    if not context:
        return "Odev cozumu kaydi bos gorunuyor. PDF'i tekrar yuklemeni oneririm."

    prompt = (
        "Sen JARVIS'in odev cevaplama modusun.\n"
        "Asagida daha once PDF'ten cikarilip cozulmus odev cevaplari var. "
        "Kullanicinin sordugu spesifik soruya bu kayda gore cevap ver.\n\n"
        "Kurallar:\n"
        "- Yaniti Turkce, kisa ve net ver.\n"
        "- Test sorusuysa sik harfini ve cevabi soyle.\n"
        "- Gerekirse 1 cumlelik aciklama ekle.\n"
        "- Kayitta yoksa 'Bu soru kayitta bulunamadi' de ve yakin eslesenleri belirt.\n\n"
        f"Kullanici sorusu: {query}\n\n"
        f"Odev cozumu:\n{context}"
    )

    client = genai.Client(api_key=api_key)
    last_error: Exception | None = None
    for model_name in HOMEWORK_MODELS:
        for attempt, delay in enumerate((0.7, 1.4, 2.4), start=1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Part.from_text(text=prompt)],
                    config=types.GenerateContentConfig(temperature=0.1),
                )
                text = _extract_response_text(response)
                return text or "Bu soru icin cevap uretilemedi."
            except Exception as exc:
                last_error = exc
                if attempt < 3 and _is_transient_error(exc):
                    time.sleep(delay)
                    continue
                if _is_transient_error(exc):
                    break
                return _friendly_error(exc)

    assert last_error is not None
    return _friendly_error(last_error)


def get_homework_status() -> str:
    data = load_active_homework()
    if not data or data.get("status") != "ready":
        return "Hazir odev yok. Odev menusunden PDF yukleyebilirsin."

    solution = data.get("solution", {})
    title = str(solution.get("title", "Odev") if isinstance(solution, dict) else "Odev")
    count = len(solution.get("questions", []) or []) if isinstance(solution, dict) else 0
    processed_at = str(data.get("processed_at", ""))
    return f"{title}: {count} soru hazir. Islenme zamani: {processed_at}"
