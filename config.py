import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Anthropic API ────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 4096

# ─── Agent Settings ───────────────────────────────────────────
AGENT_TIMEOUT = 30        # seconds before agent times out
MAX_RETRIES = 3           # retry failed agent calls this many times

# ─── Financial Data Settings ──────────────────────────────────
DEFAULT_PERIOD = "2y"     # 2 years of historical data
DEFAULT_INTERVAL = "1d"   # daily candles
BENCHMARK_TICKER = "SPY"  # S&P 500 ETF as benchmark

# ─── Technical Indicators ─────────────────────────────────────
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BBANDS_PERIOD = 20

# ─── RAG Settings ─────────────────────────────────────────────
CHUNK_SIZE = 512          # characters per chunk for SEC filings
CHUNK_OVERLAP = 50        # overlap between chunks
TOP_K_RESULTS = 5         # number of chunks to retrieve
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # fast, free, runs locally
CHROMA_DB_PATH = "./output/chromadb"

# ─── SEC EDGAR Settings ───────────────────────────────────────
SEC_FILING_TYPES = ["10-K", "10-Q"]
MAX_FILINGS = 2           # most recent filings to analyze

# ─── Output Settings ──────────────────────────────────────────
REPORTS_DIR = "./output/reports"
REPORT_FORMAT = "markdown"

# ─── Validate API Key ─────────────────────────────────────────
if not ANTHROPIC_API_KEY:
    raise ValueError(
        "ANTHROPIC_API_KEY not found. "
        "Please add it to your .env file."
    )