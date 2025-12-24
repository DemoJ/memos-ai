import logging
from openai import OpenAI
from app.core.config import settings
from typing import List, Dict, Any, Iterator
import httpx
import re


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def filter_sensitive_content(context: str) -> str:
    """从上下文中过滤敏感信息"""
    # 将笔记内容按分隔符拆分
    notes = context.split("---")
    
    sensitive_keywords = ["密码", "password", "密钥", "token"]
    sensitive_tags = ["#密码"]
    
    def is_sensitive(note_content: str) -> bool:
        # 检查关键词
        if any(keyword in note_content.lower() for keyword in sensitive_keywords):
            return True
        # 检查标签
        if any(re.search(rf'{tag}\b', note_content, re.IGNORECASE) for tag in sensitive_tags):
            return True
        return False

    filtered_notes = [note for note in notes if not is_sensitive(note)]
    
    num_filtered = len(notes) - len(filtered_notes)
    if num_filtered > 0:
        logger.info(f"已从上下文中过滤 {num_filtered} 条敏感笔记")
        
    return "---".join(filtered_notes)


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
                    {"role": "system", "content": "你是一个有用的助手，根据用户的问题决定使用哪个工具。请仅返回工具调用。"},
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
        
        # 在生成答案前过滤上下文
        filtered_context = filter_sensitive_content(context)
        
        prompt = f"""请回答用户的问题。
用户笔记中的上下文：
---
{filtered_context}
---
用户的问题：{question}
"""
        try:
            stream = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个为 Memos 设计的 AI 助手。你的目标是成为一个有用的伙伴，通过你的分析来丰富用户的笔记。在回答时，请将用户笔记中提供的上下文作为你的主要参考，但我们鼓励你在此基础上进行扩展，加入你自己的见解和知识，以提供更全面、更深入的回答。"},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating answer with context: {e}", exc_info=True)
            yield "抱歉，生成回答时遇到错误。"

    def validate_context_relevance(self, question: str, context: str) -> bool:
        logger.info(f"Validating context relevance for question: '{question}'")
        prompt = f"""
用户问题: "{question}"

上下文:
---
{context}
---

提供的上下文是否与用户问题相关，并且可以用来回答问题？
请仅用 "是" 或 "否" 回答。
"""
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个相关性检查助手。你唯一的任务是判断提供的上下文是否有助于回答用户的问题。请仅用 '是' 或 '否' 回答。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0
            )
            answer = response.choices[0].message.content.strip().lower()
            logger.info(f"Relevance validation response: '{answer}'")
            return "是" in answer
        except Exception as e:
            logger.error(f"Error validating context relevance: {e}", exc_info=True)
            return False

    def generate_answer_without_context(self, question: str) -> Iterator[str]:
        logger.info(f"Generating answer for question '{question}' without context.")
        try:
            stream = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个乐于助人的助手。请尽你所能回答用户的问题。"},
                    {"role": "user", "content": question}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating answer without context: {e}", exc_info=True)
            yield "抱歉，生成回答时遇到错误。"

    def extract_keywords(self, question: str, max_keywords: int = 5) -> List[str]:
        """Extracts keywords from a question using the LLM."""
        import json
        logger.info(f"Extracting keywords from question: '{question}'")
        
        prompt = f"""
        请从以下用户问题中提取最相关的关键词用于数据库搜索。
        以 JSON 字符串列表的格式返回关键词。
        例如，对于问题 "如何更新我的 K3S 证书？"，输出应为 ["K3S", "证书", "更新"]。
        返回的关键词不要超过 {max_keywords} 个。

        问题: "{question}"
        """
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是关键词提取专家。请仅以 JSON 字符串列表的格式回应。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            # The model might return a JSON object with a key, e.g., {"keywords": ["a", "b"]}
            # Or it might return a direct list. We need to handle both.
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    # Look for a key that contains a list
                    for key, value in result.items():
                        if isinstance(value, list):
                            return value
                elif isinstance(result, list):
                    return result
            except (json.JSONDecodeError, TypeError):
                logger.error(f"Failed to parse keywords from LLM response: {content}")

            return []

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}", exc_info=True)
            return []

llm_service = LLMService()