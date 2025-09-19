import faiss
import numpy as np
from typing import List, Tuple
import os
import pickle
import requests
from app.core.config import settings

class VectorStore:
    def __init__(self):
        self.model = None
        self.dimension = None # Will be set on first embedding
        self.index = None
        self.id_map = {}
        self.load_or_create_index()
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        headers = {
            'Authorization': f'Bearer {settings.embedding_api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": settings.embedding_model,
            "input": texts
        }
        try:
            # Combine base URL from settings with the specific endpoint path
            url = f"{settings.embedding_api_url.rstrip('/')}/v1/embeddings"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            embeddings = np.array([item['embedding'] for item in data['data']])
            return embeddings
        except requests.exceptions.RequestException as e:
            print(f"Error calling embedding API: {e}")
            raise
        except (KeyError, IndexError) as e:
            print(f"Failed to parse API response. Unexpected format: {e}")
            raise

    def load_or_create_index(self):
        index_path = os.path.join(settings.vector_db_path, "faiss.index")
        map_path = os.path.join(settings.vector_db_path, "id_map.pkl")
        
        if os.path.exists(index_path) and os.path.exists(map_path):
            self.index = faiss.read_index(index_path)
            if self.dimension is None:
                self.dimension = self.index.d
            with open(map_path, 'rb') as f:
                self.id_map = pickle.load(f)
        else:
            os.makedirs(settings.vector_db_path, exist_ok=True)
            if self.dimension:
                self.index = faiss.IndexFlatIP(self.dimension)
    
    def add_documents(self, documents: List[str], doc_ids: List[int]) -> List[int]:
        if not documents:
            return []
        
        embeddings = self._get_embeddings(documents)
        
        if self.index is None:
            self.dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(self.dimension)

        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        start_idx = self.index.ntotal
        self.index.add(embeddings.astype(np.float32))
        
        for i, doc_id in enumerate(doc_ids):
            self.id_map[start_idx + i] = doc_id
        
        self.save_index()
        return [start_idx + i for i in range(len(documents))]
    
    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_embedding = self._get_embeddings([query])
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