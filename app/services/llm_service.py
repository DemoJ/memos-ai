import logging
from openai import OpenAI
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
                    {"role": "system", "content": "You are a direct Q&A assistant. Your sole task is to answer the user's question based *only* on the provided 'Context'. You must use the information from the context. If the context contains code, commands, or steps, present them directly as the answer. Do not invent answers or apologize if the context isn't perfect."},
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

    def validate_context_relevance(self, question: str, context: str) -> bool:
        logger.info(f"Validating context relevance for question: '{question}'")
        prompt = f"""
User Question: "{question}"

Context:
---
{context}
---

Is the provided Context relevant to the User Question and can it be used to answer the question?
Answer with only "yes" or "no".
"""
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a relevance-checking assistant. Your only job is to determine if the provided context can help answer the user's question. Respond with only 'yes' or 'no' in lowercase."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0
            )
            answer = response.choices[0].message.content.strip().lower()
            logger.info(f"Relevance validation response: '{answer}'")
            return "yes" in answer
        except Exception as e:
            logger.error(f"Error validating context relevance: {e}", exc_info=True)
            return False

    def generate_answer_without_context(self, question: str) -> Iterator[str]:
        logger.info(f"Generating answer for question '{question}' without context.")
        try:
            stream = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Answer the user's question to the best of your ability."},
                    {"role": "user", "content": question}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating answer without context: {e}", exc_info=True)
            yield "Sorry, an error occurred while generating the answer."

    def extract_keywords(self, question: str, max_keywords: int = 5) -> List[str]:
        """Extracts keywords from a question using the LLM."""
        import json
        logger.info(f"Extracting keywords from question: '{question}'")
        
        prompt = f"""
        From the following user question, extract the most relevant keywords for a database search.
        Return the keywords as a JSON list of strings.
        For example, for the question "How do I renew my K3S certificate?", the output should be ["K3S", "certificate", "renew"].
        Do not return more than {max_keywords} keywords.

        Question: "{question}"
        """
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are an expert in keyword extraction. You only respond with a JSON list of strings."},
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