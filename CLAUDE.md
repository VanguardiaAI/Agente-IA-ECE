# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eva is an AI-powered virtual customer service assistant for WooCommerce stores by vanguardia.dev. It uses the Model Context Protocol (MCP) for real-time integration and provides intelligent product search and order management through a conversational interface.

## Key Commands

### Development Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
cp env.agent.example env.agent
```

### Running the Application
```bash
# Start both MCP server and web interface
python start_services.py

# Or start individually:
python main.py  # MCP server on port 8000
python app.py   # Web interface on port 8080
```

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Run specific test scripts
python scripts/test_postgres.py
python scripts/test_woocommerce.py
python scripts/test_phase3_integration.py
```

### Docker Operations
```bash
# Start services
./scripts/docker-production.sh start

# View logs
./scripts/docker-production.sh logs

# Create backup
./scripts/docker-production.sh backup

# Restore from backup
./scripts/docker-production.sh restore backup_file.gz

# Check status
./scripts/docker-production.sh status
```

## Architecture Overview

### Core Components

1. **MCP Server (main.py)**: HTTP-based MCP server on port 8000 providing tool endpoints for product search, order management, and customer service operations.

2. **Web Interface (app.py)**: FastAPI application on port 8080 with real-time chat interface, dashboard, and webhook handling.

3. **Database Layer**: PostgreSQL with pgvector extension for hybrid search capabilities (60% vector, 40% text search using RRF).

4. **AI Agent System**: 
   - Intent classification and entity extraction
   - Conversational memory management
   - Multi-agent system with specialized agents for sales, support, and technical queries

### Key Directories

- `src/agent/`: AI agent logic including hybrid_agent.py and multi_agent_system.py
- `src/web/`: Web interfaces (interface.py, enhanced_interface.py)
- `services/`: Backend services for database, embeddings, and WooCommerce integration
- `tools/`: MCP tools for order and product management
- `config/`: Configuration management using Pydantic settings
- `docs/`: Technical documentation, deployment guide, and testing guidelines
- `tests/`: Comprehensive test suite with run_tests.py orchestrator
- `scripts/`: Utility scripts for testing and deployment

### Integration Points

1. **WooCommerce API**: Full integration for products, orders, and customer data
2. **OpenAI Embeddings**: text-embedding-3-small for semantic search
3. **LLM Support**: Both OpenAI and Anthropic models for conversation
4. **Webhooks**: Real-time updates from WooCommerce

## Important Patterns

1. **Hybrid Search**: Combines vector embeddings with text search using Reciprocal Rank Fusion (RRF) for optimal product discovery.

2. **MCP Tools**: All customer service operations are exposed as MCP tools with structured input/output using Pydantic models.

3. **Async Architecture**: FastAPI async endpoints for scalability, with proper connection pooling for database operations.

4. **Error Handling**: Comprehensive error logging and user-friendly error messages throughout the application.

5. **Configuration**: Environment-based configuration with validation using Pydantic settings.

## Development Notes

### Testing Strategy
The test runner (`tests/run_tests.py`) executes tests in sequence:
1. Connection tests (critical) - Must pass for system to function
2. Tool tests (critical) - Individual MCP tool functionality
3. Server tests (non-critical) - Full integration tests

### Database Management
- PostgreSQL with pgvector runs in Docker container
- Automated daily backups via cron job
- Manual backup/restore available through docker-production.sh

### Service Endpoints
- MCP Server: `http://localhost:8000/mcp`
- Web Interface: `http://localhost:8080`
- WebSocket: `ws://localhost:8080/ws/{client_id}`
- Health Check: `http://localhost:8000/health`

## Key Features

### Knowledge Base System
- **Markdown-based knowledge**: Store company policies, FAQs, and general information in `/knowledge` directory
- **Automatic embedding generation**: All documents are processed and searchable
- **Hybrid search**: Combines vector and text search for optimal results
- **Dynamic updates**: Run `python scripts/load_knowledge.py` to update knowledge base

### Enhanced Order Management
- **Secure order lookup**: Requires both order ID and customer email for validation
- **Privacy-focused**: Only shows order details after identity verification
- **Customer order history**: Safe listing of orders by email

### Conversation Memory
- **Persistent memory**: Remembers customer interactions across sessions
- **Context-aware responses**: Uses previous conversations for better service
- **User preferences**: Tracks and uses customer preferences
- **Automatic summaries**: Generates conversation summaries for future reference

### Incremental Product Sync
- **Efficient updates**: Only syncs changed products
- **Webhook support**: Register changes for real-time updates
- **Hash-based change detection**: Avoids unnecessary updates
- **Continuous sync**: Can run automatically every 5 minutes

### Testing
```bash
# Run complete system tests
python tests/test_complete_system.py

# Test individual components
python scripts/test_postgres.py
python scripts/test_woocommerce.py
python scripts/load_knowledge.py
```


## WhatsApp Integration (360Dialog)

### Configuration
Add to `.env`:
```env
WHATSAPP_360DIALOG_API_KEY=your_api_key
WHATSAPP_360DIALOG_API_URL=https://waba-v2.360dialog.io
WHATSAPP_PHONE_NUMBER=34123456789  # Without + or spaces
WHATSAPP_WEBHOOK_VERIFY_TOKEN=secure_random_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
```

### Setup Commands
```bash
# Configure webhook
python scripts/configure_360dialog_webhook.py --url https://your-domain.com/api/webhooks/whatsapp

# Test connection
python scripts/test_360dialog_connection.py

# Run cart recovery
python scripts/whatsapp_cart_recovery.py

# Setup ngrok tunnel for local development
./scripts/setup_whatsapp_tunnel.sh
```

### Service Components
- `services/whatsapp_360dialog_service.py` - Main WhatsApp API service
- `services/whatsapp_webhook_handler.py` - Webhook handling
- `services/whatsapp_templates.py` - Message template management
- `services/cart_abandonment_service.py` - Cart recovery automation
- `src/utils/whatsapp_utils.py` - Formatting utilities
- `src/utils/whatsapp_product_formatter.py` - Product message formatting
- `src/utils/whatsapp_interactive_formatter.py` - Interactive message builder

## WordPress Plugin

### Eva Chatbot Widget (v2.1.9)
Located in `/eva-chatbot-widget/`:
- **Features**: Real-time WebSocket chat, responsive design, WooCommerce integration
- **Installation**: Copy to `/wp-content/plugins/` and activate in WordPress
- **Configuration**: Set server URL (default: http://localhost:8080) in WordPress admin
- **Customization**: Supports hooks, custom CSS, position and color configuration

### Building Plugin ZIP
```bash
# Create plugin ZIP for distribution
cd eva-chatbot-widget
zip -r ../eva-chatbot-widget.zip . -x "*.git*" -x "node_modules/*" -x "*.DS_Store"
```

## Production Deployment

### Docker Production Setup
```bash
# Start all services with production configuration
./scripts/docker-production.sh start

# View logs
./scripts/docker-production.sh logs

# Create backup
./scripts/docker-production.sh backup

# Restore from backup
./scripts/docker-production.sh restore backup_file.gz

# Check status
./scripts/docker-production.sh status
```

### Production Environment Variables
Use `env.production.example` as template:
- Set secure passwords for PostgreSQL
- Configure production API keys
- Enable SSL/TLS settings
- Set appropriate CORS origins
- Configure rate limiting
- Setup monitoring (Sentry DSN)

### Systemd Service Setup
```bash
# Copy service files
sudo cp docs/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable eva-mcp eva-web
sudo systemctl start eva-mcp eva-web
```

### Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /mcp {
        proxy_pass http://localhost:8000;
    }
    
    location /api/webhooks/whatsapp {
        proxy_pass http://localhost:8080;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Monitoring & Maintenance
- **Logs**: Check `/opt/eva/logs/` and use `journalctl -u eva-mcp -f`
- **Backups**: Automated via cron: `0 2 * * * /opt/eva/MCP-WC/scripts/docker-production.sh backup`
- **Updates**: `git pull && pip install -r requirements.txt --upgrade && ./scripts/docker-production.sh update`
- **Health Check**: `curl http://localhost:8000/health`

## Security Considerations

### Sensitive Files (NOT in repo)
- `env.agent` - API credentials
- `docker/postgres/data/` - Database files
- `venv/` - Python virtual environment
- Any `*.key`, `*.pem`, `*.cert` files

### Best Practices
1. Rotate API keys regularly
2. Use environment variables for all secrets
3. Enable HTTPS for all production endpoints
4. Implement rate limiting for public APIs
5. Regular security audits and dependency updates
6. Monitor access logs for suspicious activity

## Current State

The project has completed Phase 3 with all major features implemented:
- ✅ Knowledge base system with RAG
- ✅ Secure order validation
- ✅ Persistent conversation memory
- ✅ Incremental product synchronization
- ✅ Enhanced agent with knowledge integration
- ✅ Comprehensive test suite
- ✅ WhatsApp Business API integration via 360Dialog
- ✅ WordPress chat widget plugin (eva-chatbot-widget)

The system is production-ready for El Corte Eléctrico with 4,677+ products and full customer service capabilities.