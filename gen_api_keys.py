#!/usr/bin/env python3
"""Generate strong API keys for radarvan.

Usage:
    python gen_api_keys.py

Prints the generated keys and the Heroku CLI commands to set them.
"""
import secrets

READ_KEY = secrets.token_urlsafe(32)
WRITE_KEY = secrets.token_urlsafe(32)

for keyname in ["FRONTEND_KEY", "ZULUCLIENT_KEY", "BILLS_KEY", "CNCSTATS_KEY"]:
    with open(keyname, 'w') as f:
        f.write(f"RADARVAN_API_KEY={secrets.token_urlsafe(32)}")
