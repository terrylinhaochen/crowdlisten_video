from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent  # crowdlisten_marketing/
load_dotenv(BASE_DIR / ".env")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")

FONT_PATH         = "/System/Library/Fonts/Supplemental/Impact.ttf"
PROCESSING_DIR    = BASE_DIR / "processing"
REELS_OUTPUT_DIR  = BASE_DIR / "reels_output"
PUBLISHED_DIR     = BASE_DIR / "published"
MARKETING_CLIPS_DIR = BASE_DIR / "marketing_clips"
BRAND_ASSETS_DIR  = BASE_DIR / "brand_assets"
LOGO_PATH         = str(BRAND_ASSETS_DIR / "CRD.png")
TMP_DIR           = BASE_DIR / "studio" / "tmp"
QUEUE_FILE        = BASE_DIR / "studio" / "queue.json"

# Ensure runtime dirs exist
TMP_DIR.mkdir(parents=True, exist_ok=True)
PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
