"""
Tesfa AI Root Agent Loader

This module serves as the entry point for the agent system.
It imports and exports the root_agent, which is required by Google ADK
to discover and load the agent.

The actual agent configuration is in agent.py - this file is just
a simple re-export for ADK's agent discovery mechanism.
"""

from .agent import root_agent