"""
Servicio de embeddings usando OpenAI
Maneja la generación de vectores semánticos para la búsqueda híbrida
"""

import asyncio
import openai
from typing import List, Dict, Any, Optional
from config.settings import settings, EMBEDDING_CONFIG
import logging
import time

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Servicio para generar embeddings usando OpenAI"""
    
    def __init__(self):
        self.client = None
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.chunk_size = EMBEDDING_CONFIG["chunk_size"]
        self.chunk_overlap = EMBEDDING_CONFIG["chunk_overlap"]
        self.batch_size = EMBEDDING_CONFIG["batch_size"]
        self.initialized = False
    
    async def initialize(self):
        """Inicializar el servicio de embeddings"""
        try:
            if not settings.OPENAI_API_KEY:
                raise Exception("OPENAI_API_KEY no configurado")
            
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Probar conexión
            test_success = await self.test_connection()
            if test_success:
                self.initialized = True
                logger.info("✅ Servicio de embeddings inicializado correctamente")
            else:
                raise Exception("Prueba de conexión con OpenAI falló")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio de embeddings: {e}")
            self.initialized = False
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generar embedding para un texto"""
        if not self.initialized:
            raise Exception("Servicio de embeddings no inicializado")
            
        try:
            # Limpiar y preparar texto
            clean_text = self._prepare_text(text)
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=clean_text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generar embeddings para múltiples textos en lotes"""
        embeddings = []
        
        # Procesar en lotes para evitar límites de API
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_clean = [self._prepare_text(text) for text in batch]
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch_clean
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                # Pequeña pausa para evitar rate limiting
                if len(texts) > self.batch_size:
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error en lote de embeddings: {e}")
                # En caso de error, generar embeddings individuales
                for text in batch:
                    try:
                        embedding = await self.generate_embedding(text)
                        embeddings.append(embedding)
                    except:
                        # Embedding vacío en caso de error total
                        embeddings.append([0.0] * 1536)
        
        return embeddings
    
    def _prepare_text(self, text: str) -> str:
        """Preparar texto para embedding"""
        if not text:
            return ""
        
        # Limpiar texto básico
        clean_text = text.strip()
        
        # Truncar si es muy largo (OpenAI tiene límites)
        if len(clean_text) > self.max_tokens * 4:  # Aproximadamente 4 chars por token
            clean_text = clean_text[:self.max_tokens * 4]
        
        return clean_text
    
    def chunk_text(self, text: str) -> List[str]:
        """Dividir texto largo en chunks manejables"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Si no es el último chunk, buscar un punto de corte natural
            if end < len(text):
                # Buscar el último espacio o punto antes del límite
                last_space = text.rfind(' ', start, end)
                last_period = text.rfind('.', start, end)
                
                cut_point = max(last_space, last_period)
                if cut_point > start:
                    end = cut_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Mover el inicio con overlap
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    async def generate_product_embedding(self, product: Dict[str, Any]) -> List[float]:
        """Generar embedding específico para productos"""
        # Preparar texto del producto para embedding
        product_text = self._prepare_product_text(product)
        return await self.generate_embedding(product_text)
    
    def _prepare_product_text(self, product: Dict[str, Any]) -> str:
        """Preparar texto de producto para embedding"""
        parts = []
        
        # Nombre del producto (más importante)
        name = product.get('name', '')
        if name:
            parts.append(f"Producto: {name}")
        
        # Descripción corta
        short_desc = product.get('short_description', '')
        if short_desc:
            # Limpiar HTML básico
            clean_desc = short_desc.replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
            parts.append(f"Descripción: {clean_desc}")
        
        # Descripción larga (si existe y es diferente)
        long_desc = product.get('description', '')
        if long_desc and long_desc != short_desc:
            clean_long = long_desc.replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
            # Limitar longitud de descripción larga
            if len(clean_long) > 500:
                clean_long = clean_long[:500] + "..."
            parts.append(f"Detalles: {clean_long}")
        
        # SKU
        sku = product.get('sku', '')
        if sku:
            parts.append(f"SKU: {sku}")
        
        # Categorías
        categories = product.get('categories', [])
        if categories:
            cat_names = [cat.get('name', '') for cat in categories if cat.get('name')]
            if cat_names:
                parts.append(f"Categorías: {', '.join(cat_names)}")
        
        # Etiquetas/Tags
        tags = product.get('tags', [])
        if tags:
            tag_names = [tag.get('name', '') for tag in tags if tag.get('name')]
            if tag_names:
                parts.append(f"Etiquetas: {', '.join(tag_names)}")
        
        # Precio (importante para búsquedas)
        price = product.get('price', '')
        if price:
            parts.append(f"Precio: ${price}")
        
        # Estado de stock
        stock_status = product.get('stock_status', '')
        if stock_status:
            status_text = "En stock" if stock_status == 'instock' else "Sin stock"
            parts.append(f"Disponibilidad: {status_text}")
        
        # Atributos técnicos
        attributes = product.get('attributes', [])
        if attributes:
            attr_texts = []
            for attr in attributes:
                name = attr.get('name', '')
                options = attr.get('options', [])
                if name and options:
                    attr_texts.append(f"{name}: {', '.join(options)}")
            
            if attr_texts:
                parts.append(f"Especificaciones: {'; '.join(attr_texts)}")
        
        return ' | '.join(parts)
    
    async def generate_company_info_embedding(self, info: Dict[str, Any]) -> List[float]:
        """Generar embedding para información de empresa"""
        info_text = self._prepare_company_text(info)
        return await self.generate_embedding(info_text)
    
    def _prepare_company_text(self, info: Dict[str, Any]) -> str:
        """Preparar texto de información de empresa"""
        parts = []
        
        title = info.get('title', '')
        if title:
            parts.append(f"Tema: {title}")
        
        content = info.get('content', '')
        if content:
            parts.append(f"Información: {content}")
        
        category = info.get('category', '')
        if category:
            parts.append(f"Categoría: {category}")
        
        keywords = info.get('keywords', [])
        if keywords:
            parts.append(f"Palabras clave: {', '.join(keywords)}")
        
        return ' | '.join(parts)
    
    async def test_connection(self) -> bool:
        """Probar conexión con OpenAI"""
        try:
            if not self.client:
                return False
                
            # Hacer una llamada directa sin pasar por generate_embedding
            response = await self.client.embeddings.create(
                model=self.model,
                input="test connection"
            )
            
            return len(response.data[0].embedding) > 0
        except Exception as e:
            logger.error(f"Error probando conexión OpenAI: {e}")
            return False

# Instancia global del servicio de embeddings
embedding_service = EmbeddingService() 