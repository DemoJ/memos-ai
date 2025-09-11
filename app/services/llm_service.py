import logging
from openai import OpenAI, APIError
from app.core.config import settings
from typing import List, Dict, Any, Iterator
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
    
    def decide_tool(self, question: str, tools: List[Dict[str, Any]]):
        logger.info(f"Deciding tool for question: '{question}'")
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that decides which tool to use based on the user's question. Respond with only the tool call."},
                    {"role": "user", "content": question}
                ],
                tools=tools,
                tool_choice="auto"
            )
            return response.choices[0].message
        except Exception as e:
            logger.error(f"Error deciding tool: {e}", exc_info=True)
            return None

    def generate_answer_with_context(self, question: str, context: str) -> Iterator[str]:
        logger.info(f"Generating answer for question '{question}' with provided context.")
        
        prompt = f"""Based on the following context, please answer the user's question.
Context:
---
{context}
---
Question: {question}
"""
        try:
            stream = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating answer with context: {e}", exc_info=True)
            yield "Sorry, an error occurred while generating the answer."

llm_service = LLMService()