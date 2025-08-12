#!/usr/bin/env python
"""
Automatic update script for products and knowledge base
Runs twice daily to keep information up-to-date
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.incremental_sync import IncrementalSyncService
from services.woocommerce import WooCommerceService
from services.database import HybridDatabaseService as DatabaseService
from services.embedding_service import EmbeddingService
from config.settings import settings

# Configure logging
log_dir = Path("/opt/eva/logs")
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

async def update_products():
    """Update products from WooCommerce"""
    logger.info("Starting product synchronization...")
    
    try:
        # Initialize services
        woo_service = WooCommerceService()  # No parameters needed
        
        db_service = DatabaseService()  # No parameters needed
        await db_service.initialize()
        
        embedding_service = EmbeddingService()  # No parameters needed
        await embedding_service.initialize()
        
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
        logger.error(f"Error updating products: {str(e)}")
        raise

async def update_knowledge_base():
    """Update knowledge base embeddings"""
    logger.info("Starting knowledge base update...")
    
    try:
        # Run the knowledge loading script
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/load_knowledge.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            logger.info("Knowledge base update completed successfully")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"Knowledge base update failed: {result.stderr}")
            raise Exception(f"Knowledge base update failed with code {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}")
        raise

async def send_notification(success: bool, details: dict):
    """Send notification about update status"""
    status = "SUCCESS" if success else "FAILED"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"""
📊 Eva Auto Update Report - {timestamp}
Status: {status}

Products Update:
- Added: {details.get('products', {}).get('added', 0)}
- Updated: {details.get('products', {}).get('updated', 0)}
- Deleted: {details.get('products', {}).get('deleted', 0)}
- Errors: {details.get('products', {}).get('errors', 0)}

Knowledge Base: {'✅ Updated' if details.get('knowledge_success') else '❌ Failed'}

Next update scheduled in 12 hours.
"""
    
    logger.info(message)
    
    # Write to status file for monitoring
    status_file = Path("/opt/eva/logs/update_status.txt")
    with open(status_file, 'w') as f:
        f.write(f"{timestamp}|{status}|{details}\n")

async def main():
    """Main update function"""
    logger.info("=== Starting Eva Auto Update ===")
    start_time = datetime.now()
    
    details = {
        'products': {},
        'knowledge_success': False
    }
    
    try:
        # Update products
        try:
            products_result = await update_products()
            details['products'] = products_result
        except Exception as e:
            logger.error(f"Product update failed: {e}")
            details['products']['error'] = str(e)
        
        # Update knowledge base
        try:
            knowledge_result = await update_knowledge_base()
            details['knowledge_success'] = knowledge_result
        except Exception as e:
            logger.error(f"Knowledge base update failed: {e}")
            details['knowledge_error'] = str(e)
        
        # Determine overall success
        success = bool(details['products'] and not details['products'].get('error')) or details['knowledge_success']
        
        # Send notification
        await send_notification(success, details)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Update completed in {duration:.2f} seconds ===")
        
    except Exception as e:
        logger.error(f"Critical error in auto update: {e}")
        await send_notification(False, {'error': str(e)})
        raise

if __name__ == "__main__":
    asyncio.run(main())