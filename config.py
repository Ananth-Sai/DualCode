import os
import logging
import warnings
from dotenv import load_dotenv

# Suppress google.genai internal AFC and deprecation warnings
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="google.genai")

load_dotenv()

# Gemini / Model Settings
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
WRITER_MODEL: str = os.getenv("WRITER_MODEL", "gemini-3.5-flash-lite")
CRITIC_MODEL: str = os.getenv("CRITIC_MODEL", "gemini-flash-lite-latest")
FALLBACK_MODELS: list[str] = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3.5-flash-lite",
]

# Generation Hyperparameters
WRITER_TEMPERATURE: float = 0.3
CRITIC_TEMPERATURE: float = 0.0

# Orchestrator Loop Parameters
MAX_ROUNDS: int = 3
STALL_THRESHOLD: float = 0.98

# Sandbox Execution Parameters
TEST_TIMEOUT_SECONDS: int = 5
