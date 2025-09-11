import os
import sys

# Add project root to Python path to allow importing app modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # It's important to import the instance, not the class
    from app.services.vector_store import vector_store
    print(f"Successfully loaded vector store.")
    print(f"Number of vectors in Faiss index: {vector_store.index.ntotal}")
    print(f"Number of items in ID map: {len(vector_store.id_map)}")
    # Print some sample data to verify
    print(f"ID map keys (first 10): {list(vector_store.id_map.keys())[:10]}")
    print(f"ID map values (first 10): {list(vector_store.id_map.values())[:10]}")

except ImportError as e:
    print(f"Failed to import vector_store: {e}")
    print("Please ensure that the script is run from the project root and all dependencies are installed.")
except Exception as e:
    print(f"An error occurred: {e}")