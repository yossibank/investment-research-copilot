from pathlib import Path

# parents[0] → research_copilot/
# parents[1] → src/
# parents[2] → backend/
# parents[3] → リポジトリのルート
REPO_ROOT = Path(__file__).resolve().parents[3]

ENV_PATH = REPO_ROOT / ".env"

DATA_DIR = REPO_ROOT / "data"

CACHE_DIR = DATA_DIR / "cache"

EVALUATION_DIR = REPO_ROOT / "evaluation"

PAGES_PATH = DATA_DIR / "parsed" / "pages.json"

CHUNKS_PATH = CACHE_DIR / "chunks.json"

EMBEDDINGS_PATH = CACHE_DIR / "embeddings.npy"
