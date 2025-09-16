"""
🎯 Results Validator Agent V2 - FULLY AI-POWERED
No more mechanical responses, only intelligent AI-based decisions
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from .agent_interfaces import (
    IResultsValidatorAgent,
    SearchResults,
    ValidationResult,
    ProductUnderstanding
)

# Load configuration
load_dotenv("env.agent")

from openai import OpenAI

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)

class AIResultsValidatorAgent(IResultsValidatorAgent):
    """
    COMPLETELY AI-POWERED Results Validator
    
    Key principles:
    - AI decides everything, no hardcoded rules
    - No mechanical responses
    - Context-aware, intelligent decisions
    - Only asks for refinement when AI determines it's truly necessary
    """
    
    def __init__(self):
        self.logger = logger
        self.name = "AIResultsValidator"
        
    async def validate(self, *args, **kwargs):
        """Main validation method"""
        return await self.validate_results(*args, **kwargs)
    
    async def process(self, *args, **kwargs):
        """Process method required by interface"""
        return await self.validate_results(*args, **kwargs)
    
    async def generate_refinement_question(self, understanding: ProductUnderstanding, search_results: SearchResults) -> str:
        """Generate refinement question - required by interface"""
        # Let AI decide if refinement is needed
        decision = await self._ai_evaluate_and_decide(search_results, understanding, "")
        
        if decision.get("needs_refinement"):
            return decision.get("refinement_question", "")
        return ""
    
    async def validate_results(
        self,
        search_results: SearchResults,
        original_request: str,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """
        AI-POWERED validation of search results
        """
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🤖 AI Validator: Analyzing {search_results.total_count} results")
            
            # Case: No results
            if not search_results.products or search_results.total_count == 0:
                return await self._ai_handle_no_results(understanding, original_request)
            
            # Let AI evaluate EVERYTHING
            ai_decision = await self._ai_evaluate_and_decide(
                search_results,
                understanding,
                original_request
            )
            
            # Extract AI's decision
            needs_refinement = ai_decision.get("needs_refinement", False)
            refinement_question = ai_decision.get("refinement_question")
            validation_score = ai_decision.get("confidence_score", 0.7)
            products_to_show = ai_decision.get("products_to_show", [])
            
            # Select the best products based on AI's evaluation
            valid_products = []
            if isinstance(products_to_show, list):
                for idx in products_to_show[:20]:  # Max 20 products
                    if isinstance(idx, int) and idx < len(search_results.products):
                        product = search_results.products[idx]
                        if product:
                            valid_products.append(product)
            
            # If AI didn't specify products, take top ones
            if not valid_products and search_results.products:
                max_products = 5 if needs_refinement else 10
                for product in search_results.products[:max_products]:
                    if product:
                        valid_products.append(product)
            
            self.logger.info(f"🤖 AI Decision:")
            self.logger.info(f"   Needs refinement: {needs_refinement}")
            self.logger.info(f"   Confidence: {validation_score:.2f}")
            self.logger.info(f"   Products to show: {len(valid_products)}")
            if refinement_question:
                self.logger.info(f"   Question: {refinement_question[:100]}...")
            
            return ValidationResult(
                valid_products=valid_products,
                invalid_products=[],
                needs_refinement=needs_refinement,
                refinement_question=refinement_question,
                validation_score=validation_score,
                rejection_reasons=ai_decision.get("issues", [])
            )
            
        except Exception as e:
            self.logger.error(f"AI Validator error: {e}")
            # Intelligent fallback
            return self._simple_fallback(search_results, understanding)
    
    async def _ai_evaluate_and_decide(
        self,
        search_results: SearchResults,
        understanding: ProductUnderstanding,
        original_query: str
    ) -> Dict[str, Any]:
        """
        CORE AI EVALUATION - This is where the magic happens
        AI decides EVERYTHING based on understanding the situation
        """
        
        # Prepare product samples for AI
        product_samples = []
        for i, product in enumerate(search_results.products[:15] if search_results.products else []):
            if product:
                product_samples.append({
                    "index": i,
                    "name": (product.get("name") or "")[:100],
                    "brand": product.get("brand", ""),
                    "price": product.get("price", 0),
                    "category": product.get("category", ""),
                    "sku": product.get("sku", "")
                })
        
        prompt = f"""You are an expert electrical store assistant evaluating search results.
Your job is to decide if the results are good enough to show to the customer or if we need to ask for more information.

CUSTOMER REQUEST: "{original_query}"

WHAT WE UNDERSTOOD:
- Product type: {understanding.product_type or "not identified"}
- Brand: {understanding.brand or "not specified"}
- Specifications: {json.dumps(understanding.specifications, ensure_ascii=False) if understanding.specifications else "none"}

SEARCH RESULTS:
- Total found: {search_results.total_count}
- Sample products:
{json.dumps(product_samples, indent=2, ensure_ascii=False)}

ANALYZE AND DECIDE:

1. Are these results GOOD ENOUGH to show to the customer?
2. Do we REALLY need to ask for more information?

IMPORTANT GUIDELINES:
- If you found 1-5 highly relevant products → DON'T ask for refinement
- If you found 6-15 relevant products → Usually DON'T ask for refinement
- If you found 16-30 mixed products → Consider asking ONLY if results are too diverse
- If you found 30+ products → Ask for refinement ONLY if they're all over the place
- If customer was specific (brand + specs) → Almost NEVER ask for refinement
- If products match the request reasonably well → DON'T ask for refinement

RESPOND WITH JSON:
{{
    "needs_refinement": false,  // true ONLY if absolutely necessary
    "confidence_score": 0.85,  // 0.0 to 1.0, your confidence in the results
    "refinement_question": null,  // ONLY if needs_refinement is true, be SPECIFIC
    "products_to_show": [0, 1, 2],  // indices of best products to show (up to 10)
    "reasoning": "Brief explanation",  // Why this decision?
    "issues": []  // Any problems found (empty if results are good)
}}

REFINEMENT QUESTION GUIDELINES (only if needed):
- For DIFFERENTIALS → Ask: "¿Necesitas el diferencial de 25A, 40A o 63A? ¿Con sensibilidad de 30mA o 300mA?"
- For CABLES → Ask: "¿Qué sección de cable necesitas? Tenemos 1.5mm², 2.5mm², 4mm² y 6mm²"
- For MAGNETOTÉRMICOS → Ask: "¿De qué amperaje lo necesitas? Tenemos de 10A, 16A, 20A y 25A"
- For LAMPS → Ask: "¿Qué potencia necesitas? ¿Es para interior o exterior?"
- Be SPECIFIC, mention actual options available

Remember: The goal is to HELP the customer, not to annoy them with unnecessary questions.
Default to showing results unless they're truly inadequate."""

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert electrical store assistant. Be helpful but not annoying."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                ),
                timeout=5.0  # 5 second timeout
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Ensure refinement question is in Spanish if provided
            if result.get("refinement_question") and not any(spanish_word in result["refinement_question"].lower() 
                                                             for spanish_word in ["qué", "necesitas", "para", "tenemos"]):
                # AI returned English, translate the concept
                result["refinement_question"] = self._translate_refinement_concept(
                    understanding.product_type,
                    result.get("reasoning", "")
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI evaluation error: {e}")
            # Simple decision fallback
            return {
                "needs_refinement": search_results.total_count > 30,
                "confidence_score": 0.7 if search_results.total_count < 20 else 0.5,
                "refinement_question": None,
                "products_to_show": list(range(min(10, search_results.total_count))),
                "reasoning": "Fallback decision",
                "issues": []
            }
    
    async def _ai_handle_no_results(
        self,
        understanding: ProductUnderstanding,
        original_query: str
    ) -> ValidationResult:
        """AI handles the no results case"""
        
        prompt = f"""The customer searched for "{original_query}" but we found NO products.
We understood they want: {understanding.product_type or 'unknown product'}
Brand: {understanding.brand or 'any'}

Generate a helpful Spanish response asking them to:
1. Try different search terms
2. Or describe what they need differently
3. Be natural and helpful, not robotic

Just return the question in Spanish, nothing else."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful Spanish-speaking store assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            question = response.choices[0].message.content.strip()
            
        except Exception as e:
            question = f"No encontré {understanding.product_type or 'ese producto'}. ¿Podrías describir qué necesitas de otra forma?"
        
        return ValidationResult(
            valid_products=[],
            invalid_products=[],
            needs_refinement=True,
            refinement_question=question,
            validation_score=0.0,
            rejection_reasons=["No products found"]
        )
    
    def _translate_refinement_concept(self, product_type: str, reasoning: str) -> str:
        """Translate refinement concept to proper Spanish question"""
        
        product_type_lower = (product_type or "").lower()
        
        if "diferencial" in product_type_lower:
            return "¿Qué amperaje necesitas para el diferencial? Tenemos de 25A, 40A y 63A, con sensibilidad de 30mA o 300mA"
        elif "cable" in product_type_lower:
            return "¿Qué sección de cable necesitas? Disponemos de 1.5mm², 2.5mm², 4mm² y 6mm²"
        elif "magnetot" in product_type_lower:
            return "¿De qué amperaje necesitas el magnetotérmico? Tenemos de 10A, 16A, 20A y 25A"
        elif "lámpara" in product_type_lower or "lamp" in product_type_lower:
            return "¿Qué potencia de lámpara buscas? ¿Es para interior o exterior?"
        elif "enchufe" in product_type_lower:
            return "¿Buscas enchufe schuko o industrial? ¿Para empotrar o superficie?"
        else:
            return f"¿Podrías darme más detalles sobre el {product_type} que necesitas?"
    
    def _simple_fallback(
        self,
        search_results: SearchResults,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """Simple fallback when AI fails"""
        
        # Simple logic: few products = good, many products = maybe refine
        if search_results.total_count <= 10:
            needs_refine = False
            score = 0.8
        elif search_results.total_count <= 25:
            needs_refine = False
            score = 0.7
        else:
            needs_refine = True
            score = 0.5
        
        question = None
        if needs_refine:
            if not understanding.brand:
                question = "Hay varias opciones disponibles. ¿Tienes alguna marca preferida?"
            else:
                question = f"Encontré muchos {understanding.product_type or 'productos'}. ¿Qué características específicas necesitas?"
        
        return ValidationResult(
            valid_products=search_results.products[:10] if search_results.products else [],
            invalid_products=[],
            needs_refinement=needs_refine,
            refinement_question=question,
            validation_score=score,
            rejection_reasons=[]
        )