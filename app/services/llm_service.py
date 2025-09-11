import logging
from openai import OpenAI, APIError
from app.core.config import settings
from typing import List, Dict, Any
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class LLMService:
    def __init__(self):
        # Diagnostic code to check the loaded httpx version and path
        logger.info(f"httpx version: {httpx.__version__}")
        logger.info(f"httpx path: {httpx.__file__}")

        # To isolate the persistent TypeError, we simplify the client initialization.
        # The transport argument is temporarily removed to check for conflicts.
        http_client = httpx.Client(
            proxy=settings.proxy if settings.proxy else None
        )
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            http_client=http_client
        )
    
    def generate_answer(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        if not context_docs:
            logger.warning("No context documents found for the question.")
            return "根据我现有的笔记，找不到相关信息。"
        
        context_text = "\n\n".join([
            f"笔记 {i+1}:\n{doc['content']}"
            for i, doc in enumerate(context_docs)
        ])
        
        prompt = f"""请根据以下我的笔记内容来回答问题。如果笔记中没有相关信息，请明确说明"根据我现有的笔记，找不到相关信息"。

我的笔记内容：
{context_text}

问题：{question}

回答："""

        try:
            logger.info(f"Generating answer for question: '{question}'")
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个基于用户个人笔记的问答助手。请根据提供的笔记内容准确回答问题，不要添加笔记中没有的信息。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info("Successfully generated answer.")
            return answer
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"抱歉，调用LLM API时出现错误：{e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            return f"抱歉，生成回答时出现了未知错误：{str(e)}"

llm_service = LLMService()