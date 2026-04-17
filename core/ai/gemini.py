# FILE: core/ai/gemini.py
# @core-candidate: GeminiClient, 2026-04, Gemini API 연동 및 프롬프트 관리

import os
import logging
from typing import List, Dict, Any, Optional, Union, Generator
from google import genai
from google.genai import types
from dotenv import load_dotenv

log = logging.getLogger(__name__)

class GeminiClient:
    """
    Google Gemini API (google-genai)를 간편하게 사용하기 위한 클라이언트 래퍼입니다.
    """

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model_name: str = "gemini-2.5-flash",
        system_instruction: Optional[str] = None
    ):
        """
        Args:
            api_key (str): Gemini API 키. 생략 시 .env 파일이나 환경변수(GEMINI_API_KEY)를 로드합니다.
            model_name (str): 사용할 모델 이름 (기본: gemini-2.5-flash)
            system_instruction (str): 시스템 프롬프트 (Role 설정 등)
        """
        # .env 파일 로드
        load_dotenv()
        
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API 키가 필요합니다. 환경변수 'GEMINI_API_KEY'를 설정하거나 "
                "생성자 인자로 전달해주세요."
            )
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.system_instruction = system_instruction

    def generate(
        self, 
        prompt: str, 
        stream: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> Union[str, Generator[str, None, None]]:
        """
        텍스트 프롬프트에 대한 응답을 생성합니다.
        """
        # 03_llm_pipeline.py의 reference 방식을 따라 types.GenerateContentConfig 사용
        gen_config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=config.get("temperature", 0.1) if config else 0.1,
            max_output_tokens=config.get("max_output_tokens") if config else None,
        )

        try:
            if stream:
                return self._generate_stream(prompt, gen_config)
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=gen_config
                )
                return response.text
        except Exception as e:
            log.error(f"Gemini API 호출 중 오류 발생: {e}")
            raise

    def _generate_stream(self, prompt: str, config: types.GenerateContentConfig) -> Generator[str, None, None]:
        """스트리밍 응답 내부 처리"""
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config
        ):
            if chunk.text:
                yield chunk.text

    def chat(self, messages: List[Dict[str, str]], config: Optional[Dict[str, Any]] = None) -> str:
        """
        멀티턴 대화를 수행합니다.
        """
        contents = []
        for msg in messages:
            contents.append(types.Content(
                role=msg['role'],
                parts=[types.Part.from_text(text=msg['content'])]
            ))

        gen_config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=config.get("temperature", 0.1) if config else 0.1,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=gen_config
        )
        return response.text

if __name__ == "__main__":
    # 간단 테스트 (API 키가 환경변수에 있을 때)
    logging.basicConfig(level=logging.INFO)
    try:
        gemini = GeminiClient(system_instruction="당신은 주식 전문가입니다. 한국어로 답변하세요.")
        print(gemini.generate("삼성전자의 전망에 대해 짧게 말해줘."))
    except Exception as e:
        print(f"테스트 실패 (API 키 확인 필요): {e}")
