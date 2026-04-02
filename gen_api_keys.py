#!/usr/bin/env python3
"""Generate strong API keys for radarvan.

Usage:
    python gen_api_keys.py

Prints the generated keys and the Heroku CLI commands to set them.
"""
import secrets

READ_KEY = secrets.token_urlsafe(32)
WRITE_KEY = secrets.token_urlsafe(32)

print("Generated API keys:")
print(f"  API_KEY_READ  = {READ_KEY}")
print(f"  API_KEY_WRITE = {WRITE_KEY}")
print()
print("Set on Heroku:")
print(f"  heroku config:set API_KEY_READ={READ_KEY} API_KEY_WRITE={WRITE_KEY} -a radarvan-5e9c302c60e6")
print()
print("Set for local frontend (.env.local):")
print(f"  VITE_API_KEY={WRITE_KEY}")
