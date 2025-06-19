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
        "CFTC": "https://www.cftc.gov/PressRoom/PressReleases", 
        "FDIC": "https://www.fdic.gov/news/press-releases/",  
        "FINRA": "https://www.finra.org/media-center/newsreleases", 
        "Federal Reserve Board": "https://www.federalreserve.gov/newsevents/pressreleases.htm",  
    },
    "EU": {
        "ESMA": "https://www.esma.europa.eu/press-news/esma-news",  
        "EBA": "https://www.eba.europa.eu/publications-and-media",  
        "EIOPA": "https://www.eiopa.europa.eu/media/news_en",  
        "European Parliament News": "https://www.europarl.europa.eu/news/en/press-room",  
        "ECB": "https://www.ecb.europa.eu/press/pr/html/index.en.html",  
    },
    "Asia": {
        "Japan FSA": "https://www.fsa.go.jp/en/news/",  
        "Reserve Bank of India (RBI)": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",  
    },
    "Global": {
        "BIS": "https://www.bis.org/press/index.htm",  
        "IMF": "https://www.imf.org/en/News",  
        "World Bank": "https://www.worldbank.org/en/news/all",  
        "OECD": "https://www.oecd.org/newsroom/",  
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

