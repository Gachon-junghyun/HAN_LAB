# FILE: core/ai/__init__.py
import logging

log = logging.getLogger(__name__)

# OllamaClient는 로컬 환경에 ollama가 있을 경우 항상 사용 가능하게 시도
try:
    from .ollama import OllamaClient
except ImportError:
    OllamaClient = None
    log.warning("OllamaClient를 로드할 수 없습니다. 'pip install ollama'가 필요합니다.")

# GeminiClient는 Google GenAI 라이브러리가 필요함
try:
    from .gemini import GeminiClient
except ImportError:
    GeminiClient = None
    log.warning("GeminiClient를 로드할 수 없습니다. 'pip install google-genai'가 필요합니다.")

__all__ = ["GeminiClient", "OllamaClient"]
