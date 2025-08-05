# Eva MCP-WC Documentation

## Overview
Eva is an AI-powered virtual customer service assistant for WooCommerce stores. It uses Model Context Protocol (MCP) for tool integration and provides intelligent product search through hybrid vector/text search.

## Documentation Index

### Core Documentation
- [Technical Documentation](TECHNICAL_DOCUMENTATION.md) - Complete system architecture, API reference, and configuration
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Setup instructions for development and production
- [Testing Guide](TESTING.md) - Test suite documentation and validation procedures

### Implementation Phases
- [Phase 1 - Hybrid Search](README_FASE1_BUSQUEDA_HIBRIDA.md) - PostgreSQL + pgvector implementation
- [Phase 2 - Complete System](README_FASE2_COMPLETA.md) - Full integration with WooCommerce
- [AI Agent Documentation](README_AGENT_ACTUALIZADO.md) - Conversational AI configuration

### Operations
- [Docker Production Setup](DOCKER_PRODUCCION_SETUP.md) - Container deployment and management

## Quick Links

### Development
- Start Services: `python start_services.py`
- Run Tests: `python tests/run_tests.py`
- API Docs: http://localhost:8080/docs

### Production
- Docker Deploy: `./scripts/docker-production.sh start`
- Health Check: http://localhost:8000/health
- Dashboard: http://localhost:8080/dashboard

## System Status
- **Current Phase**: Phase 3 (AI Agent Enhancement)
- **Products Indexed**: 4,677
- **Search Type**: Hybrid (60% vector, 40% text)
- **Supported LLMs**: OpenAI GPT-4, Anthropic Claude