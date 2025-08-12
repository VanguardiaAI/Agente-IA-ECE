#!/usr/bin/env python
"""
Automatic update script for Docker environment
Optimized for running inside containers with proper networking
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import subprocess

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.incremental_sync import IncrementalSyncService
from services.woocommerce import WooCommerceService
from services.database import HybridDatabaseService as DatabaseService
from services.embedding_service import EmbeddingService
from config.settings import settings

# Configure logging
log_dir = Path("/app/logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"auto_update_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def wait_for_postgres():
    """Wait for PostgreSQL to be ready"""
    logger.info("Waiting for PostgreSQL connection...")
    max_retries = 30
    retry_delay = 2
    
    for i in range(max_retries):
        try:
            db_service = DatabaseService()  # No parameters needed
            await db_service.initialize()
            await db_service.close()
            logger.info("PostgreSQL is ready!")
            return True
        except Exception as e:
            if i < max_retries - 1:
                logger.debug(f"PostgreSQL not ready, retrying in {retry_delay}s... ({i+1}/{max_retries})")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"PostgreSQL connection failed after {max_retries} attempts: {e}")
                return False
    
    return False

async def update_products():
    """Update products from WooCommerce"""
    logger.info("Starting product synchronization...")
    
    try:
        # Ensure PostgreSQL is ready
        if not await wait_for_postgres():
            raise Exception("PostgreSQL is not available")
        
        # Initialize services
        woo_service = WooCommerceService()  # No parameters needed
        
        db_service = DatabaseService()  # No parameters needed
        await db_service.initialize()
        
        embedding_service = EmbeddingService(settings.OPENAI_API_KEY)
        
        sync_service = IncrementalSyncService(
            woo_service=woo_service,
            db_service=db_service,
            embedding_service=embedding_service
        )
        
        # Run synchronization
        result = await sync_service.sync_products()
        
        logger.info(f"Product sync completed: {result}")
        logger.info(f"Added: {result['added']}, Updated: {result['updated']}, "
                   f"Deleted: {result['deleted']}, Errors: {result['errors']}")
        
        await db_service.close()
        return result
        
    except Exception as e:
        logger.error(f"Error updating products: {str(e)}", exc_info=True)
        return {
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 1,
            'error': str(e)
        }

async def update_knowledge_base():
    """Update knowledge base embeddings"""
    logger.info("Starting knowledge base update...")
    
    try:
        # Check if knowledge directory exists
        knowledge_dir = Path("/app/knowledge")
        if not knowledge_dir.exists():
            logger.warning("Knowledge directory not found, skipping knowledge base update")
            return False
        
        # Run the knowledge loading script
        env = os.environ.copy()
        env['PYTHONPATH'] = '/app'
        
        result = subprocess.run(
            [sys.executable, "/app/scripts/load_knowledge.py"],
            capture_output=True,
            text=True,
            cwd="/app",
            env=env
        )
        
        if result.returncode == 0:
            logger.info("Knowledge base update completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Knowledge base update failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}", exc_info=True)
        return False

async def write_status(success: bool, details: dict):
    """Write status to file for monitoring"""
    try:
        status = "SUCCESS" if success else "FAILED"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Write to status file
        status_file = Path("/app/logs/update_status.txt")
        with open(status_file, 'w') as f:
            f.write(f"{timestamp}|{status}|{details}\n")
        
        # Also write a JSON status for easier parsing
        import json
        json_status = {
            'timestamp': timestamp,
            'success': success,
            'products': details.get('products', {}),
            'knowledge': details.get('knowledge_success', False)
        }
        
        json_file = Path("/app/logs/update_status.json")
        with open(json_file, 'w') as f:
            json.dump(json_status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error writing status: {e}")

async def main():
    """Main update function"""
    logger.info("=== Starting Eva Auto Update (Docker) ===")
    logger.info(f"Environment: POSTGRES_HOST={os.getenv('POSTGRES_HOST', 'not set')}")
    logger.info(f"DATABASE_URL={settings.DATABASE_URL[:30]}...")
    
    start_time = datetime.now()
    
    details = {
        'products': {},
        'knowledge_success': False
    }
    
    try:
        # Update products
        products_result = await update_products()
        details['products'] = products_result
        
        # Update knowledge base
        knowledge_result = await update_knowledge_base()
        details['knowledge_success'] = knowledge_result
        
        # Determine overall success
        success = (
            details['products'] and 
            'error' not in details['products'] and 
            details['products'].get('errors', 0) == 0
        ) or details['knowledge_success']
        
        # Write status
        await write_status(success, details)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Update completed in {duration:.2f} seconds ===")
        logger.info(f"Overall status: {'SUCCESS' if success else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Critical error in auto update: {e}", exc_info=True)
        await write_status(False, {'error': str(e)})
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())