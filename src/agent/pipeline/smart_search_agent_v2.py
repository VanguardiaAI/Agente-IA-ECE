"""
🔍 Smart Search Agent V2 - AI-POWERED QUERY GENERATION
Creates truly tailored search queries using AI, not just passing raw queries
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from .agent_interfaces import (
    ISmartSearchAgent,
    SearchResults,
    ProductUnderstanding,
    SearchError
)

# Load configuration
load_dotenv("env.agent")

from openai import OpenAI

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import database services
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.database import db_service
from services.embedding_service import embedding_service as embeddings_service

logger = logging.getLogger(__name__)

class AISmartSearchAgent(ISmartSearchAgent):
    """
    AI-POWERED Search Agent that creates tailored queries
    
    Key improvements:
    - AI generates optimized search queries
    - Multiple search strategies executed in parallel
    - Intelligent query refinement
    - No more raw query passing
    """
    
    def __init__(self):
        super().__init__(name="AISmartSearch")
        self._db_initialized = False
        self._embeddings_initialized = False
        self.logger.info("🚀 AI Smart Search Agent V2 initialized")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> SearchResults:
        """Process the product understanding and execute search"""
        if isinstance(input_data, ProductUnderstanding):
            understanding = input_data
        else:
            understanding = ProductUnderstanding(
                search_query=input_data.get("search_query", ""),
                product_type=input_data.get("product_type"),
                brand=input_data.get("brand"),
                specifications=input_data.get("specifications", {}),
                synonyms_applied=input_data.get("synonyms_applied", []),
                confidence=input_data.get("confidence", 0.5)
            )
        
        return await self.search_products(understanding)
    
    async def search_products(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Execute AI-powered product search with tailored queries
        """
        
        # Ensure services are initialized
        await self._ensure_services_initialized()
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🤖 AI Search for: '{understanding.search_query}'")
            
            # Step 1: AI generates tailored search queries
            search_queries = await self._ai_generate_search_queries(understanding)
            
            self.logger.info(f"📝 AI generated {len(search_queries)} tailored queries")
            for q in search_queries[:3]:
                self.logger.info(f"   - {q['query'][:50]} ({q['strategy']})")
            
            # Step 2: Execute searches with tailored queries
            all_results = []
            for query_info in search_queries[:3]:  # Execute top 3 strategies
                results = await self._execute_tailored_search(
                    query_info,
                    understanding,
                    filters
                )
                if results and results.products:
                    all_results.extend(results.products)
            
            # Step 3: Deduplicate and rank results using AI
            final_products = await self._ai_rank_and_deduplicate(
                all_results,
                understanding
            )
            
            # Step 4: Create final SearchResults
            time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            search_result = SearchResults(
                products=final_products,
                total_count=len(final_products),
                search_strategy="ai_multi_strategy",
                query_used=search_queries[0]["query"] if search_queries else understanding.search_query,
                filters_applied=filters or {}
            )
            
            self.logger.info(f"✅ AI Search completed: {len(final_products)} unique products")
            self.logger.info(f"   Time: {time_ms}ms")
            
            return search_result
            
        except Exception as e:
            self.logger.error(f"AI Search error: {e}")
            # Fallback to simple search
            return await self._fallback_simple_search(understanding)
    
    async def _ai_generate_search_queries(
        self,
        understanding: ProductUnderstanding
    ) -> List[Dict[str, Any]]:
        """
        AI generates multiple tailored search queries
        """
        
        prompt = f"""You are an expert at searching electrical products in a Spanish database.
Generate OPTIMIZED search queries to find what the customer wants.

CUSTOMER REQUEST: "{understanding.search_query}"

WHAT WE KNOW:
- Product type: {understanding.product_type or "not identified"}
- Brand: {understanding.brand or "any"}
- Specifications: {json.dumps(understanding.specifications, ensure_ascii=False) if understanding.specifications else "none"}

IMPORTANT: The database contains Spanish electrical products. Common terms:
- Diferencial (circuit breaker)
- Magnetotérmico (thermal magnetic breaker)
- Cable, Enchufe, Interruptor, Lámpara, Contador, etc.

GENERATE MULTIPLE SEARCH STRATEGIES:

1. EXACT: Most specific query with all details
2. TYPE_FOCUSED: Focus on product type with key specs
3. BRAND_FOCUSED: Brand + basic type (if brand exists)
4. BROAD: Broader search to catch related products
5. ALTERNATIVE: Alternative terms or synonyms

Return JSON array with search queries:
[
    {{
        "strategy": "exact",
        "query": "the optimized search query",
        "reasoning": "why this query"
    }},
    ...
]

RULES:
- Remove filler words (por favor, necesito, busco, quiero)
- Keep technical specifications (25A, 30mA, 2.5mm²)
- Use Spanish electrical terms
- Be specific but not too narrow
- Each query should be different

Example:
Request: "necesito un diferencial schneider de 40A"
Queries:
- "diferencial schneider 40A 30mA" (exact)
- "diferencial 40A" (type_focused)
- "schneider diferencial" (brand_focused)
- "diferencial 40" (broad)
- "interruptor diferencial 40A schneider" (alternative)"""

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating search queries for electrical products."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=400
                ),
                timeout=5.0  # 5 second timeout
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            queries = json.loads(content)
            
            # Ensure we have valid queries
            if not queries:
                raise ValueError("No queries generated")
            
            return queries
            
        except Exception as e:
            self.logger.error(f"AI query generation error: {e}")
            # Fallback queries
            return self._generate_fallback_queries(understanding)
    
    async def _execute_tailored_search(
        self,
        query_info: Dict[str, Any],
        understanding: ProductUnderstanding,
        filters: Optional[Dict]
    ) -> SearchResults:
        """
        Execute search with a tailored query
        """
        
        query = query_info["query"]
        strategy = query_info["strategy"]
        
        try:
            # Choose search method based on strategy
            if strategy in ["exact", "type_focused"]:
                # Use hybrid search for precision
                embedding = await embeddings_service.generate_embedding(query)
                results = await db_service.hybrid_search(
                    query_text=query,
                    query_embedding=embedding,
                    limit=20
                )
            elif strategy == "brand_focused" and understanding.brand:
                # Text search focusing on brand
                results = await db_service.text_search(
                    query_text=query,
                    limit=25
                )
            else:
                # Vector search for broader matches
                embedding = await embeddings_service.generate_embedding(query)
                results = await db_service.vector_search(
                    query_embedding=embedding,
                    limit=30,
                    min_similarity=0.5
                )
            
            # Format results
            products = []
            for r in results:
                if r:
                    product = {
                        "product_id": r.get("product_id"),
                        "sku": r.get("sku"),
                        "name": r.get("name"),
                        "description": r.get("description"),
                        "price": r.get("price"),
                        "stock": r.get("stock_quantity", 0),
                        "category": r.get("category"),
                        "brand": r.get("brand"),
                        "score": r.get("score", 0),
                        "image_url": r.get("image_url"),
                        "_strategy": strategy  # Track which strategy found it
                    }
                    products.append(product)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy=strategy,
                query_used=query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Search execution error for {strategy}: {e}")
            return SearchResults(
                products=[],
                total_count=0,
                search_strategy=f"{strategy}_error",
                query_used=query,
                filters_applied={}
            )
    
    async def _ai_rank_and_deduplicate(
        self,
        all_products: List[Dict],
        understanding: ProductUnderstanding
    ) -> List[Dict]:
        """
        AI ranks and deduplicates products
        """
        
        if not all_products:
            return []
        
        # Deduplicate by product_id or SKU
        seen = set()
        unique_products = []
        
        for product in all_products:
            if product:
                key = product.get("product_id") or product.get("sku")
                if key and key not in seen:
                    seen.add(key)
                    unique_products.append(product)
        
        # If we have few products, return them all
        if len(unique_products) <= 10:
            return unique_products
        
        # For many products, let AI rank them
        try:
            product_list = []
            for i, p in enumerate(unique_products[:30]):  # Limit to 30 for AI
                product_list.append({
                    "index": i,
                    "name": (p.get("name") or "")[:80],
                    "brand": p.get("brand", ""),
                    "price": p.get("price", 0),
                    "strategy": p.get("_strategy", "unknown")
                })
            
            prompt = f"""Rank these products by relevance to the customer's request.

CUSTOMER WANTS: {understanding.product_type or understanding.search_query}
Brand preference: {understanding.brand or "none"}
Specifications: {json.dumps(understanding.specifications, ensure_ascii=False) if understanding.specifications else "none"}

PRODUCTS FOUND:
{json.dumps(product_list, indent=2, ensure_ascii=False)}

Return JSON array of top 10-15 product indices in order of relevance:
[0, 5, 2, 8, ...] 

Only include indices of truly relevant products."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at ranking product relevance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse indices
            if "[" in content:
                indices_str = content[content.find("["):content.find("]")+1]
                indices = json.loads(indices_str)
                
                # Return ranked products
                ranked = []
                for idx in indices[:15]:  # Max 15 products
                    if idx < len(unique_products):
                        ranked.append(unique_products[idx])
                
                return ranked if ranked else unique_products[:10]
            
        except Exception as e:
            self.logger.error(f"AI ranking error: {e}")
        
        # Fallback: return first 10 unique products
        return unique_products[:10]
    
    def _generate_fallback_queries(self, understanding: ProductUnderstanding) -> List[Dict]:
        """
        Generate fallback queries when AI fails
        """
        queries = []
        
        # Original query
        queries.append({
            "strategy": "original",
            "query": understanding.search_query,
            "reasoning": "Original customer query"
        })
        
        # Type-focused if available
        if understanding.product_type:
            queries.append({
                "strategy": "type_focused",
                "query": understanding.product_type,
                "reasoning": "Product type search"
            })
        
        # Brand-focused if available
        if understanding.brand:
            brand_query = f"{understanding.brand}"
            if understanding.product_type:
                brand_query += f" {understanding.product_type}"
            queries.append({
                "strategy": "brand_focused",
                "query": brand_query,
                "reasoning": "Brand search"
            })
        
        return queries
    
    async def _fallback_simple_search(self, understanding: ProductUnderstanding) -> SearchResults:
        """
        Simple fallback search when AI fails
        """
        try:
            # Try hybrid search with original query
            embedding = await embeddings_service.generate_embedding(understanding.search_query)
            results = await db_service.hybrid_search(
                query_text=understanding.search_query,
                query_embedding=embedding,
                limit=20
            )
            
            products = []
            for r in results:
                if r:
                    products.append({
                        "product_id": r.get("product_id"),
                        "sku": r.get("sku"),
                        "name": r.get("name"),
                        "description": r.get("description"),
                        "price": r.get("price"),
                        "stock": r.get("stock_quantity", 0),
                        "category": r.get("category"),
                        "brand": r.get("brand"),
                        "score": r.get("score", 0),
                        "image_url": r.get("image_url")
                    })
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="fallback_hybrid",
                query_used=understanding.search_query,
                filters_applied={}
            )
            
        except Exception as e:
            self.logger.error(f"Fallback search error: {e}")
            return SearchResults(
                products=[],
                total_count=0,
                search_strategy="error",
                query_used=understanding.search_query,
                filters_applied={}
            )
    
    async def _ensure_services_initialized(self):
        """Ensure database and embedding services are initialized"""
        if not self._db_initialized:
            if not db_service.initialized:
                await db_service.initialize()
            self._db_initialized = True
        
        if not self._embeddings_initialized:
            # Initialize embeddings service
            if not embeddings_service.initialized:
                await embeddings_service.initialize()
            self._embeddings_initialized = True
    
    async def search_by_category(self, category: str, limit: int = 20) -> SearchResults:
        """Search products by category - required by interface"""
        understanding = ProductUnderstanding(
            search_query=category,
            product_type=category,
            brand=None,
            specifications={},
            synonyms_applied=[],
            confidence=0.8
        )
        return await self.search_products(understanding)
    
    async def search_similar(self, product_id: str, limit: int = 10) -> SearchResults:
        """Search similar products - required by interface"""
        # For now, return empty results as this requires product details
        return SearchResults(
            products=[],
            total_count=0,
            search_strategy="similar",
            query_used=f"similar to {product_id}",
            filters_applied={}
        )