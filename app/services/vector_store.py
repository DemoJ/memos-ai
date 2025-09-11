import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional
import os
import pickle
from app.core.config import settings

class VectorStore:
    def __init__(self):
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = None
        self.id_map = {}
        self.load_or_create_index()
    
    def load_or_create_index(self):
        index_path = os.path.join(settings.vector_db_path, "faiss.index")
        map_path = os.path.join(settings.vector_db_path, "id_map.pkl")
        
        if os.path.exists(index_path) and os.path.exists(map_path):
            self.index = faiss.read_index(index_path)
            with open(map_path, 'rb') as f:
                self.id_map = pickle.load(f)
        else:
            os.makedirs(settings.vector_db_path, exist_ok=True)
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def add_documents(self, documents: List[str], doc_ids: List[int]) -> List[int]:
        if not documents:
            return []
        
        embeddings = self.model.encode(documents, convert_to_numpy=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        start_idx = self.index.ntotal
        self.index.add(embeddings.astype(np.float32))
        
        for i, doc_id in enumerate(doc_ids):
            self.id_map[start_idx + i] = doc_id
        
        self.save_index()
        return [start_idx + i for i in range(len(documents))]
    
    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        if self.index.ntotal == 0:
            return []
        
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx in self.id_map and idx != -1:
                memo_id = self.id_map[idx]
                results.append((memo_id, float(score)))
        
        return results
    
    def delete_documents(self, doc_ids: List[int]):
        indices_to_remove = [k for k, v in self.id_map.items() if v in doc_ids]
        
        if indices_to_remove:
            self.index.remove_ids(np.array(indices_to_remove))
            for idx in indices_to_remove:
                del self.id_map[idx]
            self.save_index()
    
    def save_index(self):
        index_path = os.path.join(settings.vector_db_path, "faiss.index")
        map_path = os.path.join(settings.vector_db_path, "id_map.pkl")
        
        faiss.write_index(self.index, index_path)
        with open(map_path, 'wb') as f:
            pickle.dump(self.id_map, f)

vector_store = VectorStore()