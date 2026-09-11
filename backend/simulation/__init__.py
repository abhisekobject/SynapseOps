"""SynapseOps Simulation Module — Phase 2.

Provides a controllable simulated infrastructure environment for
developing and testing the SynapseOps intelligence pipeline.

Architecture:
    The simulation module manages:
    - Failure state (what failures are currently active)
    - Failure injection API (inject / clear / query)
    - Pre-defined failure scenarios (named, reproducible)

    Simulated services (gateway, api_service, worker) are separate
    FastAPI applications that run alongside the main backend and read
    their failure state from Redis.
"""
