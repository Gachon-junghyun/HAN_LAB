# FILE: core/ai/ollama.py
import logging
from typing import List, Dict, Any, Optional, Union, Generator
try:
    import ollama
except ImportError:
    ollama = None

log = logging.getLogger(__name__)

class OllamaClient:
    """
    Ollama 공식 라이브러리를 사용한 로컬 AI 연동 클라이언트입니다.
    """

    def __init__(
        self, 
        model_name: str = "llama3", 
        host: Optional[str] = "http://localhost:11434"
    ):
        if ollama is None:
            raise ImportError("ollama 패키지가 설치되어 있지 않습니다. 'pip install ollama'를 실행하세요.")
        
        self.client = ollama.Client(host=host)
        self.model_name = model_name

    def generate(
        self, 
        prompt: str, 
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[str, Generator[str, None, None]]:
        """
        단순 텍스트 프롬프트에 대한 응답을 생성합니다.
        """
        try:
            if stream:
                return self._generate_stream(prompt, options)
            else:
                response = self.client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options=options
                )
                return response['response']
        except Exception as e:
            log.error(f"Ollama Generate 오류: {e}")
            raise

    def _generate_stream(self, prompt: str, options: Optional[Dict[str, Any]]) -> Generator[str, None, None]:
        """스트리밍 응답 처리"""
        for chunk in self.client.generate(model=self.model_name, prompt=prompt, stream=True, options=options):
            yield chunk['response']

    def chat(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[str, Generator[str, None, None]]:
        """
        메시지 리스트를 통한 대화형 응답을 생성합니다.
        messages 예시: [{'role': 'user', 'content': '안녕?'}]
        """
        try:
            if stream:
                return self._chat_stream(messages, options)
            else:
                response = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    options=options
                )
                return response['message']['content']
        except Exception as e:
            log.error(f"Ollama Chat 오류: {e}")
            raise

    def _chat_stream(self, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]]) -> Generator[str, None, None]:
        """대화 스트리밍 응답 처리"""
        for chunk in self.client.chat(model=self.model_name, messages=messages, stream=True, options=options):
            yield chunk['message']['content']

    def list_models(self) -> List[str]:
        """로컬에 설치된 모델 목록을 반환합니다."""
        models = self.client.list()
        return [m['name'] for m in models['models']]

if __name__ == "__main__":
    # 간단 테스트
    logging.basicConfig(level=logging.INFO)
    try:
        # 모델명은 실제 설치된 모델로 변경 필요 (예: llama3, gemma, qwen)
        client = OllamaClient(model_name="qwen2.5:0.5b") 
        print(f"설치된 모델: {client.list_models()}")
        
        print("\n[Generate 테스트]")
        print(client.generate("1+1은?"))
        
        print("\n[Chat 스트리밍 테스트]")
        for chunk in client.chat([{'role': 'user', 'content': '자기소개 10자 이내로.'}], stream=True):
            print(chunk, end="", flush=True)
        print()
    except Exception as e:
        print(f"테스트 실패: {e}")
