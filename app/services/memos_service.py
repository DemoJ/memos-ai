from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Memo
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.core.config import settings
from typing import List, Dict, Any, Iterator
import os

class MemosService:
    def __init__(self):
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'memos_prod.db'))
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_memo_by_id(self, memo_id: int) -> Memo:
        with self.SessionLocal() as session:
            return session.query(Memo).filter(Memo.id == memo_id).first()
    
    def get_all_active_memos(self) -> List[Memo]:
        with self.SessionLocal() as session:
            return session.query(Memo).filter(
                Memo.row_status == "NORMAL",
                Memo.visibility == "PRIVATE"
            ).all()
    
    def search_memos(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        search_results = vector_store.search(query, k=limit)
        
        # Log search results for debugging
        print(f"Search query: {query}")
        print(f"Search results: {search_results}")
        
        results = []
        for memo_id, score in search_results:
            # Filter out results with a score below the threshold
            if score < settings.retrieval_score_threshold:
                continue
            
            memo = self.get_memo_by_id(memo_id)
            if memo:
                results.append({
                    "id": memo.id,
                    "content": memo.content,
                    "score": score,
                    "created_at": memo.created_datetime.isoformat(),
                    "updated_at": memo.updated_datetime.isoformat()
                })
        
        return results
    
    def get_latest_memos(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            # 移除 row_status 和 visibility 过滤器，以确保能获取到最新的笔记
            latest_memos = session.query(Memo).order_by(Memo.created_ts.desc()).limit(limit).all()
            
            return [{
                "id": memo.id,
                "content": memo.content,
                "created_at": memo.created_datetime.isoformat(),
                "updated_at": memo.updated_datetime.isoformat()
            } for memo in latest_memos]

    def answer_question(self, question: str) -> Iterator[str]:
        import json

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_latest_memos",
                    "description": "Get the most recent memos by creation time.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "The number of recent memos to retrieve.",
                            },
                        },
                        "required": ["limit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memos",
                    "description": "Search for memos based on a semantic query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The semantic query to search for.",
                            },
                             "limit": {
                                "type": "integer",
                                "description": "The maximum number of memos to return.",
                            },
                        },
                        "required": ["query", "limit"],
                    },
                },
            },
        ]

        # Step 1: Let the LLM decide which tool to use
        tool_choice_message = llm_service.decide_tool(question, tools)

        if not tool_choice_message or not tool_choice_message.tool_calls:
            # Fallback to a standard RAG if the model doesn't choose a tool
            retrieved_memos = self.search_memos(question, limit=settings.max_search_results)
        else:
            # Step 2: Execute the chosen tool
            tool_call = tool_choice_message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "get_latest_memos":
                retrieved_memos = self.get_latest_memos(**function_args)
            elif function_name == "search_memos":
                retrieved_memos = self.search_memos(**function_args)
            else:
                # Fallback if the model hallucinates a function name
                retrieved_memos = self.search_memos(question, limit=settings.max_search_results)

        # Step 3: Generate the final answer based on the tool's output
        if not retrieved_memos:
            def empty_response():
                yield "根据我现有的笔记，找不到相关信息。"
            return empty_response()

        context = "\n\n".join([
            f"笔记 (ID: {memo['id']}, Created: {memo['created_at']}):\n{memo['content']}"
            for memo in retrieved_memos
        ])

        return llm_service.generate_answer_with_context(question, context)

memos_service = MemosService()