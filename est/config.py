import os
from dotenv import load_dotenv
load_dotenv()

PORTAL_BASE = os.getenv("PORTAL_BASE", "https://aluno.projecao.br")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
USE_LLM = os.getenv("USE_LLM", "false").lower() in ("1","true","yes","on")

LOCAL_TZ = os.getenv("LOCAL_TZ", "America/Sao_Paulo")
