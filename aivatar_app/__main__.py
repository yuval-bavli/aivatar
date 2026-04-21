"""Entry point: python -m aivatar_app"""
import asyncio
from .orchestrator import run_server

try:
    asyncio.run(run_server())
except KeyboardInterrupt:
    print("\n[orchestrator] Stopped.")
