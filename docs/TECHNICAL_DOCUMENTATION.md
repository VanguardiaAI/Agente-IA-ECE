# Technical Documentation - Eva MCP-WC System

## Overview

Eva is an AI-powered virtual customer service assistant for WooCommerce stores using Model Context Protocol (MCP) for real-time integration. The system provides intelligent product search through hybrid vector/text search and conversational order management.

## System Architecture

### Core Components

1. **MCP Server** (`main.py`)
   - HTTP-based server on port 8000
   - FastMCP framework for tool integration
   - Endpoints: `/mcp` (main), `/health`, `/tools`

2. **Web Interface** (`app.py`)
   - FastAPI application on port 8080
   - Real-time chat interface with WebSocket support
   - Dashboard with live statistics
   - Webhook handler for WooCommerce updates

3. **Database Layer**
   - PostgreSQL with pgvector extension
   - Hybrid search: 60% vector, 40% text using RRF
   - Connection pooling with asyncpg
   - Automatic reconnection on failures

4. **AI Agent System**
   - Multi-agent architecture (sales, support, technical)
   - Intent classification and entity extraction
   - Conversational memory management
   - Support for OpenAI and Anthropic models

## Configuration Reference

### Required Environment Variables

```bash
# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # Optional

# WooCommerce Configuration
WOOCOMMERCE_URL=https://your-store.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxx

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# LLM Configuration
LLM_PROVIDER=openai  # or anthropic
LLM_MODEL=gpt-4-turbo-preview  # or claude-3-opus-20240229

# Optional Settings
EMBEDDING_MODEL=text-embedding-3-small
MONGODB_URI=mongodb+srv://...  # For conversation logging
LOG_LEVEL=INFO
ENABLE_WEBHOOK_SYNC=true
```

## Hybrid Search Implementation

### Database Schema

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    sku VARCHAR(255) UNIQUE,
    price DECIMAL(10, 2),
    stock_quantity INTEGER DEFAULT 0,
    category TEXT,
    attributes JSONB,
    embedding vector(1536),
    search_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_products_search ON products USING GIN (search_vector);
CREATE INDEX idx_products_sku ON products(sku);
```

### RRF Algorithm

```python
def hybrid_search(query: str, limit: int = 10) -> List[Product]:
    # Vector search (60% weight)
    vector_results = vector_search(query, limit * 2)
    
    # Text search (40% weight)
    text_results = text_search(query, limit * 2)
    
    # Reciprocal Rank Fusion
    return reciprocal_rank_fusion(
        vector_results, 
        text_results,
        weights=[0.6, 0.4],
        k=60
    )
```

## MCP Tools

### Product Tools

1. **search_products**
   - Hybrid search with natural language queries
   - Returns top 10 most relevant products
   - Includes similarity scores

2. **get_product_details**
   - Fetch by ID or SKU
   - Full product information including variants
   - Real-time stock status

3. **check_product_stock**
   - Batch stock checking
   - Support for multiple SKUs
   - Variation-level stock info

### Order Tools

1. **get_order_status**
   - Real-time order tracking
   - Shipping information
   - Order history

2. **track_order**
   - Tracking number lookup
   - Shipping provider integration
   - Delivery estimates

## API Endpoints

### Health & Status
- `GET /health` - System health check
- `GET /api/stats` - Dashboard statistics
- `GET /api/conversations` - Conversation history

### Chat Interface
- `POST /api/chat` - Send chat message
- `WebSocket /ws/{client_id}` - Real-time chat

### Webhooks
- `POST /webhook/woocommerce` - WooCommerce updates
- Supported events: product.created, product.updated, product.deleted

## Deployment

### Docker Production Setup

```bash
# Start services
./scripts/docker-production.sh start

# View logs
./scripts/docker-production.sh logs

# Backup database
./scripts/docker-production.sh backup

# Update and restart
./scripts/docker-production.sh update
```

### Docker Compose Configuration

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: mcp_eva
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Testing

### Run All Tests
```bash
python tests/run_tests.py
```

### Individual Test Suites
- `test_postgres.py` - Database connectivity
- `test_woocommerce.py` - API integration
- `test_phase3_integration.py` - Full system test
- `test_mcp_integration.py` - MCP server validation

### Test Coverage
- Connection tests: WooCommerce, PostgreSQL, MongoDB
- Tool tests: All MCP tools individually
- Integration tests: End-to-end workflows
- Performance tests: Search latency, concurrent requests

## Monitoring & Troubleshooting

### Health Checks
```bash
# Check MCP server
curl http://localhost:8000/health

# Check web interface
curl http://localhost:8080/health

# Check database
docker exec postgres pg_isready
```

### Common Issues

1. **Embedding Sync Failures**
   - Check OpenAI API key and rate limits
   - Verify DATABASE_URL connection string
   - Run `python scripts/debug_sync_error.py`

2. **Search Performance**
   - Ensure pgvector indexes are created
   - Check embedding dimension matches (1536)
   - Monitor query execution plans

3. **WebSocket Disconnections**
   - Verify CORS settings in production
   - Check nginx WebSocket configuration
   - Enable heartbeat in client

### Debug Scripts
- `debug_woocommerce.py` - Test WooCommerce connection
- `debug_sync_error.py` - Troubleshoot sync issues
- `debug_detailed_error.py` - Analyze specific errors

## Performance Optimization

### Database
- Connection pool size: 20 (configurable)
- Statement timeout: 30s
- Automatic vacuum enabled
- Index maintenance scheduled

### Embeddings
- Batch processing: 100 products/batch
- Caching: 15-minute TTL
- Model: text-embedding-3-small (optimal cost/performance)

### Search
- Result limit: 10 default, 50 maximum
- Response time: <500ms average
- Concurrent searches: 100+ supported

## Security Considerations

1. **API Keys**: Store in environment variables only
2. **Database**: Use SSL connections in production
3. **Webhooks**: Validate signatures from WooCommerce
4. **Rate Limiting**: Implement on public endpoints
5. **CORS**: Configure allowed origins explicitly

## Current System Status

- **Products Synchronized**: 4,677 with embeddings
- **Phase 2 Complete**: Hybrid search operational
- **Phase 3 In Progress**: Enhanced AI agent
- **Success Rate**: 98.6% for API calls
- **Average Response Time**: 127ms