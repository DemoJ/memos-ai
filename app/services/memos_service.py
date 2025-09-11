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
    
    def answer_question(self, question: str) -> Iterator[str]:
        relevant_memos = self.search_memos(question, limit=settings.max_search_results)
        return llm_service.generate_answer(question, relevant_memos)

memos_service = MemosService()