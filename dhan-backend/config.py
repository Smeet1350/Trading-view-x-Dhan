# config.py
import os

# Path to the SQLite instruments DB (default: instruments.db)
SQLITE_PATH = os.getenv("INSTRUMENTS_DB", "instruments.db")

# Optional API key for webhook access.
# If empty (default) — API key check is disabled (backwards compatible).
# To enable: export WEBHOOK_API_KEY="your-secret-key"
WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "").strip()

# Optional comma-separated IP whitelist for webhook requests.
# If empty (default) — whitelist is disabled.
# Example: export WEBHOOK_IP_WHITELIST="1.2.3.4,5.6.7.8"
_raw_whitelist = os.getenv("WEBHOOK_IP_WHITELIST", "").strip()
WEBHOOK_IP_WHITELIST = [ip.strip() for ip in _raw_whitelist.split(",") if ip.strip()]

# Rate limit for webhook requests (requests per minute) — integer.
# Default 30 req/minute. Set to 0 to disable rate limiting.
WEBHOOK_RATE_LIMIT = int(os.getenv("WEBHOOK_RATE_LIMIT", "30"))

# CORS origins — comma separated. Default preserves existing localhost dev origins.
# Example: export CORS_ORIGINS="https://myapp.example.com,http://localhost:5173"
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]