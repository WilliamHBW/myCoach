"""
Embedding Service - Generate vector embeddings for text content.
Supports OpenAI and compatible embedding APIs.
"""
import httpx
from typing import List

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Embedding model configurations
EMBEDDING_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "text-embedding",
        "dimensions": 1536,
    },
}


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        config = EMBEDDING_CONFIG.get(self.provider, EMBEDDING_CONFIG["openai"])
        
        self.base_url = settings.AI_BASE_URL or config["base_url"]
        self.model = config["model"]
        self.dimensions = config["dimensions"]
        self.api_key = settings.AI_API_KEY
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Text content to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        return (await self.generate_embeddings([text]))[0]
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts.
        
        Args:
            texts: List of text contents to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        endpoint = f"{self.base_url}/embeddings"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                    },
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error", {}).get("message", str(response.status_code))
                    logger.error(
                        "Embedding API error",
                        status_code=response.status_code,
                        error=error_msg
                    )
                    raise Exception(f"Embedding API Error: {response.status_code} - {error_msg}")
                
                data = response.json()
                embeddings = [item["embedding"] for item in data.get("data", [])]
                
                logger.debug(
                    "Generated embeddings",
                    count=len(embeddings),
                    model=self.model
                )
                
                return embeddings
                
        except httpx.TimeoutException:
            logger.error("Embedding request timed out")
            raise Exception("Embedding request timed out")
        except Exception as e:
            if "Embedding API Error" not in str(e):
                logger.error("Embedding generation failed", error=str(e))
            raise
    
    def get_dimensions(self) -> int:
        """Get the embedding vector dimensions."""
        return self.dimensions

