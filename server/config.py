import os

from dotenv import load_dotenv

load_dotenv()

ES_ENDPOINT: str = os.environ["ELASTICSEARCH_ENDPOINT"]
ES_API_KEY: str = os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"]
ES_INDEX: str = os.environ.get("ES_INDEX", "eui_icons")
INFERENCE_ID: str = os.environ.get("INFERENCE_ID", "eui-icon-encoder")

GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET: str = os.environ["GOOGLE_CLIENT_SECRET"]
# Secret for signing bearer tokens. Generate with: python -c "import secrets; print(secrets.token_hex(32))"
TOKEN_SECRET: str = os.environ["TOKEN_SECRET"]
# Default 7 days: MCP clients cache the token and re-open the browser when
# it expires, so a longer lifetime keeps that to about once a week.
TOKEN_MAX_AGE_S: int = int(os.environ.get("TOKEN_MAX_AGE_S", str(7 * 24 * 3600)))

# Full base URL of this server, used to build the OAuth redirect URI.
SERVER_BASE_URL: str = os.environ.get("SERVER_BASE_URL", "http://localhost:4555")
ALLOWED_DOMAIN: str = os.environ.get("ALLOWED_DOMAIN", "elastic.co")

# Comma-separated list of origins the <IconSearch /> component is served from.
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
