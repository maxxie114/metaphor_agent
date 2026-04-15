import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-5.4"
ANNOTATOR_ID = "agent"

# Pipeline settings
MAX_CONCURRENT = 5  # max concurrent API calls
REASONING_EFFORT = "high"

# File paths
INPUT_CSV = "metaphor_selection_batch_01_1A_input.csv"
OUTPUT_CSV = "metaphor_selection_batch_01_1A_output_agent.csv"
