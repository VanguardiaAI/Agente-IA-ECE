"""
Agent Pipeline Configuration
Allows switching between different agent implementations
"""

import os
from enum import Enum

class AgentVersion(Enum):
    """Available agent versions"""
    V1 = "v1"  # Original implementations
    V2 = "v2"  # AI-powered implementations
    
# Get version from environment or default to V2
AGENT_VERSION = os.getenv("AGENT_VERSION", AgentVersion.V2.value)

def get_smart_search_agent():
    """Get the appropriate Smart Search Agent based on configuration"""
    if AGENT_VERSION == AgentVersion.V2.value:
        from .smart_search_agent_v2 import AISmartSearchAgent
        return AISmartSearchAgent()
    else:
        from .smart_search_agent import SmartSearchAgent
        return SmartSearchAgent()

def get_results_validator_agent():
    """Get the appropriate Results Validator Agent based on configuration"""
    if AGENT_VERSION == AgentVersion.V2.value:
        from .results_validator_agent_v2 import AIResultsValidatorAgent
        return AIResultsValidatorAgent()
    else:
        from .results_validator_agent_improved import ImprovedResultsValidatorAgent
        return ImprovedResultsValidatorAgent()