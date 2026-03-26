#!/usr/bin/env python3
"""
Register nanda-job-scout agents with the NANDA Index.

This script registers the Agent Fact Cards for both the Job Scout Agent
and the Interview Prep Agent with the NANDA Index registry so that other
agents on the network can discover and communicate with them.

Usage:
    # Register both agents (requires PUBLIC_URL env vars to be set):
    python scripts/register_with_nanda.py

    # Override the registry URL:
    NANDA_REGISTRY_URL=https://registry.chat39.com:6900 python scripts/register_with_nanda.py

    # Dry-run mode (prints payloads without sending):
    python scripts/register_with_nanda.py --dry-run

Environment Variables:
    NANDA_REGISTRY_URL  - NANDA Index URL   (default: https://registry.chat39.com:6900)
    SCOUT_PUBLIC_URL    - Public URL for Agent 1 (Job Scout)
    PREP_PUBLIC_URL     - Public URL for Agent 2 (Interview Prep)
"""

import argparse
import json
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DEFAULT_REGISTRY_URL = "https://registry.chat39.com:6900"


# ── Agent Definitions ──────────────────────────────────────

AGENTS = [
    {
        "agent_id": "nanda-job-scout",
        "description": (
            "AI-powered job search agent that searches the web for job listings "
            "matching a given location and keywords, then extracts structured "
            "job descriptions using an LLM."
        ),
        "public_url_env": "SCOUT_PUBLIC_URL",
        "default_port": 8080,
        "capabilities": [
            "job-search",
            "web-scraping",
            "llm-extraction",
            "structured-output",
        ],
        "tags": ["career", "jobs", "ai-recruiter", "search"],
        "agent_card_path": "/.well-known/agent.json",
    },
    {
        "agent_id": "nanda-interview-prep",
        "description": (
            "AI-powered interview preparation agent that takes structured job "
            "descriptions and a candidate resume, then generates tailored "
            "interview questions for each role."
        ),
        "public_url_env": "PREP_PUBLIC_URL",
        "default_port": 8081,
        "capabilities": [
            "interview-prep",
            "resume-parsing",
            "question-generation",
            "llm-extraction",
            "structured-output",
        ],
        "tags": ["career", "interview", "ai-coach", "resume"],
        "agent_card_path": "/.well-known/agent.json",
    },
]


# ── Registry Client Functions ──────────────────────────────


def get_registry_url() -> str:
    """Resolve the NANDA registry URL from env or default."""
    return os.getenv("NANDA_REGISTRY_URL", DEFAULT_REGISTRY_URL)


def check_registry_health(registry_url: str) -> bool:
    """Verify the NANDA registry is reachable."""
    try:
        resp = requests.get(f"{registry_url}/health", timeout=10, verify=False)
        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Registry health check failed: {e}")
        return False


def register_agent(
    registry_url: str,
    agent_id: str,
    agent_url: str,
    api_url: str,
    agent_facts_url: Optional[str] = None,
) -> bool:
    """
    Register an agent with the NANDA Index via POST /register.

    This mirrors the registration logic used by the NEST framework's
    RegistryClient and the nanda-adapter library.
    """
    data = {
        "agent_id": agent_id,
        "agent_url": agent_url,
        "api_url": api_url,
    }
    if agent_facts_url:
        data["agent_facts_url"] = agent_facts_url

    try:
        resp = requests.post(
            f"{registry_url}/register",
            json=data,
            timeout=15,
            verify=False,
        )
        if resp.status_code == 200:
            print(f"  ✓ Agent '{agent_id}' registered successfully")
            return True
        else:
            print(f"  ✗ Registration failed (HTTP {resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"  ✗ Registration error: {e}")
        return False


def update_agent_status(
    registry_url: str,
    agent_id: str,
    capabilities: list,
    tags: list,
) -> bool:
    """
    Enrich the agent's record with capabilities and tags
    via PUT /agents/<agent_id>/status.
    """
    data = {
        "alive": True,
        "capabilities": capabilities,
        "tags": tags,
    }
    try:
        resp = requests.put(
            f"{registry_url}/agents/{agent_id}/status",
            json=data,
            timeout=15,
            verify=False,
        )
        if resp.status_code == 200:
            print(f"  ✓ Agent '{agent_id}' status updated (capabilities + tags)")
            return True
        else:
            print(f"  ✗ Status update failed (HTTP {resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"  ✗ Status update error: {e}")
        return False


def verify_agent_card(agent_url: str, card_path: str) -> bool:
    """Fetch the agent card endpoint to verify it's alive."""
    try:
        resp = requests.get(f"{agent_url}{card_path}", timeout=10)
        if resp.status_code == 200:
            card = resp.json()
            print(f"  ✓ Agent card verified: {card.get('name', 'unknown')}")
            return True
        else:
            print(f"  ✗ Agent card returned HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Could not reach agent card at {agent_url}{card_path}: {e}")
        return False


# ── Main ───────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Register nanda-job-scout agents with the NANDA Index."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print registration payloads without sending them.",
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip the registry health check.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip verifying agent card endpoints are reachable.",
    )
    args = parser.parse_args()

    registry_url = get_registry_url()
    print(f"NANDA Registry: {registry_url}")
    print()

    # ── Health check ──
    if not args.dry_run and not args.skip_health:
        print("Checking registry health...")
        if not check_registry_health(registry_url):
            print("Registry is not reachable. Use --skip-health to bypass.")
            sys.exit(1)
        print("  ✓ Registry is healthy")
        print()

    # ── Register each agent ──
    success_count = 0

    for agent_def in AGENTS:
        agent_id = agent_def["agent_id"]
        public_url = os.getenv(agent_def["public_url_env"])

        if not public_url:
            print(
                f"⚠ Skipping '{agent_id}': "
                f"set {agent_def['public_url_env']} to the agent's public URL."
            )
            print()
            continue

        # Normalize: strip trailing slash
        public_url = public_url.rstrip("/")
        agent_facts_url = f"{public_url}{agent_def['agent_card_path']}"

        print(f"Registering '{agent_id}'...")
        print(f"  Public URL:      {public_url}")
        print(f"  Agent Card URL:  {agent_facts_url}")

        if args.dry_run:
            print("  [DRY RUN] Registration payload:")
            print(json.dumps({
                "agent_id": agent_id,
                "agent_url": public_url,
                "api_url": public_url,
                "agent_facts_url": agent_facts_url,
            }, indent=4))
            print("  [DRY RUN] Status update payload:")
            print(json.dumps({
                "alive": True,
                "capabilities": agent_def["capabilities"],
                "tags": agent_def["tags"],
            }, indent=4))
            print()
            success_count += 1
            continue

        # Optionally verify the agent card is reachable
        if not args.skip_verify:
            verify_agent_card(public_url, agent_def["agent_card_path"])

        # Step 1: Register with the index
        registered = register_agent(
            registry_url=registry_url,
            agent_id=agent_id,
            agent_url=public_url,
            api_url=public_url,
            agent_facts_url=agent_facts_url,
        )

        if not registered:
            print()
            continue

        # Step 2: Enrich with capabilities and tags
        update_agent_status(
            registry_url=registry_url,
            agent_id=agent_id,
            capabilities=agent_def["capabilities"],
            tags=agent_def["tags"],
        )

        success_count += 1
        print()

    # ── Summary ──
    total = len(AGENTS)
    print("=" * 50)
    print(f"Registration complete: {success_count}/{total} agents processed.")

    if success_count == total:
        print("All agents registered. They are now discoverable on the NANDA network.")
    elif success_count > 0:
        print("Some agents were skipped. Set the missing PUBLIC_URL env vars and re-run.")
    else:
        print("No agents were registered. Check your environment variables.")

    print()
    print("Next steps:")
    print("  1. Verify on the registry:  curl <registry>/lookup/nanda-job-scout")
    print("  2. List all agents:         curl <registry>/list")
    print("  3. Search by capability:    curl '<registry>/search?capabilities=job-search'")


if __name__ == "__main__":
    main()
