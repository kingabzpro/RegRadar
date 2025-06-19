import os

# API Client configurations
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
KEYWORDS_API_KEY = os.getenv("KEYWORDS_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# OpenAI base URL
OPENAI_BASE_URL = "https://api.keywordsai.co/api/"

# Regulatory websites mapping
REGULATORY_SOURCES = {
    "US": {
        "SEC": "https://www.sec.gov/news/pressreleases",
        "FDA": "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
        "FTC": "https://www.ftc.gov/news-events/news/press-releases",
        "Federal Register": "https://www.federalregister.gov/documents/current",
    },
    "EU": {
        "European Commission": "https://ec.europa.eu/commission/presscorner/home/en",
        "ESMA": "https://www.esma.europa.eu/press-news/esma-news",
        "EBA": "https://www.eba.europa.eu/news-press/news",
    },
    "Global": {
        "BIS": "https://www.bis.org/press/index.htm",
        "IOSCO": "https://www.iosco.org/news/",
    },
}

# UI settings
AVATAR_IMAGES = (
    None,
    "https://media.roboflow.com/spaces/gemini-icon.png",
)

# Default chat parameters
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_LLM_MODEL = "gpt-4.1-mini"

