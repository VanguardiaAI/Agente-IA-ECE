"""
MCP Tools for searching the knowledge base.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from services.knowledge_base import KnowledgeBaseService
from config.logging_config import logger
import asyncio


class KnowledgeSearchInput(BaseModel):
    """Input schema for searching the knowledge base."""
    query: str = Field(description="The search query to find relevant information in the knowledge base")
    limit: int = Field(default=5, description="Maximum number of results to return")


class KnowledgeResult(BaseModel):
    """Schema for a knowledge base search result."""
    content: str = Field(description="The content of the knowledge base entry")
    title: str = Field(description="The title or filename of the knowledge entry")
    similarity_score: float = Field(description="Relevance score of the result")
    category: Optional[str] = Field(description="Category of the knowledge entry if available")


class KnowledgeSearchOutput(BaseModel):
    """Output schema for knowledge base search results."""
    results: List[KnowledgeResult] = Field(description="List of relevant knowledge base entries")
    total_results: int = Field(description="Total number of results found")
    query: str = Field(description="The original search query")


async def search_knowledge(input_data: KnowledgeSearchInput) -> KnowledgeSearchOutput:
    """
    Search the knowledge base for relevant information.
    
    This tool searches through company policies, FAQs, product information,
    and other documentation stored in the knowledge base.
    
    Args:
        input_data: The search parameters
        
    Returns:
        KnowledgeSearchOutput containing relevant knowledge entries
    """
    try:
        logger.info(f"Searching knowledge base with query: {input_data.query}")
        
        # Initialize the knowledge base service
        knowledge_service = KnowledgeBaseService()
        
        # Search the knowledge base
        results = await knowledge_service.search_knowledge(
            query=input_data.query,
            limit=input_data.limit
        )
        
        # Format results
        formatted_results = []
        for result in results:
            # Extract category from metadata if available
            category = None
            if 'metadata' in result and isinstance(result['metadata'], dict):
                category = result['metadata'].get('category')
            
            formatted_results.append(KnowledgeResult(
                content=result['content'],
                title=result.get('title', 'Unknown'),
                similarity_score=result.get('combined_score', 0.0),
                category=category
            ))
        
        logger.info(f"Found {len(formatted_results)} results for query: {input_data.query}")
        
        return KnowledgeSearchOutput(
            results=formatted_results,
            total_results=len(formatted_results),
            query=input_data.query
        )
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {str(e)}")
        # Return empty results on error
        return KnowledgeSearchOutput(
            results=[],
            total_results=0,
            query=input_data.query
        )


# Tool definition for MCP server
KNOWLEDGE_TOOLS = {
    "search_knowledge": {
        "description": "Search the knowledge base for company policies, FAQs, shipping information, return policies, and other documentation",
        "input_schema": KnowledgeSearchInput,
        "output_schema": KnowledgeSearchOutput,
        "handler": search_knowledge
    }
}