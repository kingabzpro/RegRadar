from typing import List, Dict
from mem0 import MemoryClient
from config.settings import MEM0_API_KEY

# Initialize memory client
mem0_client = MemoryClient(api_key=MEM0_API_KEY)

class MemoryTools:
    def save_to_memory(self, user_id: str, query: str, response: str):
        """Save interaction to memory"""
        try:
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response},
            ]
            mem0_client.add(
                messages=messages,
                user_id=user_id,
                metadata={"type": "regulatory_query"},
            )
        except Exception as e:
            print(f"Memory save error: {e}")

    def search_memory(self, user_id: str, query: str) -> List[Dict]:
        """Search for similar past queries"""
        try:
            memories = mem0_client.search(query=query, user_id=user_id, limit=3)
            return memories
        except:
            return []

