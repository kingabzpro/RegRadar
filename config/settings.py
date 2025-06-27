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
        "Federal Register": "https://www.federalregister.gov/documents/current",
        "Federal Reserve Board": "https://www.federalreserve.gov/newsevents/pressreleases.htm",
        "CFTC": "https://www.cftc.gov/PressRoom/PressReleases",
        "FDIC": "https://www.fdic.gov/news/press-releases/",
        "FINRA": "https://www.finra.org/media-center/newsreleases",
        "FDA": "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
        "FTC": "https://www.ftc.gov/news-events/news/press-releases",
        "NIST AI RMF": "https://www.nist.gov/itl/ai-risk-management-framework",
        "FCC": "https://www.fcc.gov/news-events/press-releases",
    },
    "EU": {
        "ESMA": "https://www.esma.europa.eu/press-news/esma-news",
        "European Parliament News": "https://www.europarl.europa.eu/news/en/press-room",
        "EBA": "https://www.eba.europa.eu/publications-and-media",
        "EIOPA": "https://www.eiopa.europa.eu/media/news_en",
        "ECB": "https://www.ecb.europa.eu/press/pr/html/index.en.html",
        "EU AI Act": "https://artificialintelligenceact.eu/",
    },
    "UK": {
        "ICO": "https://ico.org.uk/about-the-ico/news-and-events/news/",
        "FCA": "https://www.fca.org.uk/news/press-releases",
        "Ofcom": "https://www.ofcom.org.uk/about-ofcom/latest/media/media-releases",
        "UK Parliament AI News": "https://www.parliament.uk/business/news/ai/",
    },
    "Asia": {
        "Japan FSA": "https://www.fsa.go.jp/en/news/",
        "Reserve Bank of India (RBI)": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "Singapore IMDA": "https://www.imda.gov.sg/news-and-events/Media-Room/Media-Releases",
        "China MIIT": "https://www.miit.gov.cn/",
    },
    "Africa": {
        "African Union": "https://au.int/en/pressreleases",
        "NTRA Egypt": "https://www.tra.gov.eg/en/media-center/news/",
        "NCC Nigeria": "https://www.ncc.gov.ng/media-centre/news-headlines",
        "ICASA South Africa": "https://www.icasa.org.za/news-events",
    },
    "Middle East": {
        "TRA UAE": "https://tdra.gov.ae/en/media-centre/news.aspx",
        "CITC Saudi Arabia": "https://www.citc.gov.sa/en/mediacenter/pressreleases/Pages/default.aspx",
        "Qatar CRA": "https://www.cra.gov.qa/en/media-center/news",
    },
    "Canada": {
        "CRTC": "https://crtc.gc.ca/eng/NEWS/RELEASES/",
        "ISED": "https://ised-isde.canada.ca/site/innovation-canada/en/news",
        "Office of the Privacy Commissioner": "https://www.priv.gc.ca/en/opc-news/news-and-announcements/",
    },
    "Australia": {
        "ACMA": "https://www.acma.gov.au/newsroom",
        "OAIC": "https://www.oaic.gov.au/about-the-OAIC/news-and-events/news-and-media-releases",
        "NSW AI Assurance Framework": "https://www.digital.nsw.gov.au/policy/artificial-intelligence/ai-assurance-framework",
    },
    "China": {
        "CAC": "http://www.cac.gov.cn/",
        "Ministry of Industry and Information Technology": "https://www.miit.gov.cn/",
        "Shanghai AI Regulations": "https://www.shanghai.gov.cn/nw12344/20220323/0001-12344_20220323_0001.html",
    },
    "India": {
        "MeitY": "https://www.meity.gov.in/press-releases",
        "TRAI": "https://www.trai.gov.in/release-publication/press-release",
        "NITI Aayog AI": "https://www.niti.gov.in/ai",
    },
    "Japan": {
        "MIC": "https://www.soumu.go.jp/english/index.html",
        "Japan AI Principles": "https://www.cas.go.jp/jp/seisaku/jinkouchinou/ai/en/ai_principles.pdf",
    },
    "Brazil": {
        "ANATEL": "https://www.anatel.gov.br/institucional/assuntos/noticias",
        "MCTIC": "http://www.mctic.gov.br/",
        "Brazil AI Law": "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2224082",
    },
    "Russia": {
        "Roskomnadzor": "https://rkn.gov.ru/news/",
        "Ministry of Digital Development": "https://digital.gov.ru/ru/events/",
    },
    "Global": {
        "IMF": "https://www.imf.org/en/News",
        "World Bank": "https://www.worldbank.org/en/news/all",
        "BIS": "https://www.bis.org/press/index.htm",
        "OECD": "https://www.oecd.org/newsroom/",
        "ITU": "https://www.itu.int/en/ITU-D/Statistics/Pages/Events/press-releases.aspx",
    },
    # Technology/AI/IT/Telecom specific
    "Technology": {
        "IEEE Standards News": "https://standards.ieee.org/news/",
        "ISO/IEC JTC 1/SC 42 (AI)": "https://www.iso.org/committee/6794475.html",
        "AI Now Institute": "https://ainowinstitute.org/reports.html",
        "OECD AI Policy Observatory": "https://oecd.ai/en/wonk/news",
    },
    "Telecom": {
        "International Telecommunication Union (ITU)": "https://www.itu.int/en/ITU-D/Statistics/Pages/Events/press-releases.aspx",
        "GSMA": "https://www.gsma.com/newsroom/press-release/",
    },
}

SOURCE_FULL_NAMES = {
    # US
    "SEC": "U.S. Securities and Exchange Commission",
    "FDA": "U.S. Food and Drug Administration",
    "FTC": "Federal Trade Commission",
    "Federal Register": "Federal Register",
    "CFTC": "Commodity Futures Trading Commission",
    "FDIC": "Federal Deposit Insurance Corporation",
    "FINRA": "Financial Industry Regulatory Authority",
    "Federal Reserve Board": "Federal Reserve Board",
    "NIST AI RMF": "National Institute of Standards and Technology AI Risk Management Framework",
    "FCC": "Federal Communications Commission",
    # EU
    "ESMA": "European Securities and Markets Authority",
    "EBA": "European Banking Authority",
    "EIOPA": "European Insurance and Occupational Pensions Authority",
    "European Parliament News": "European Parliament News",
    "ECB": "European Central Bank",
    "EU AI Act": "European Union Artificial Intelligence Act",
    # UK
    "ICO": "UK Information Commissioner's Office",
    "FCA": "UK Financial Conduct Authority",
    "Ofcom": "UK Office of Communications",
    "UK Parliament AI News": "UK Parliament Artificial Intelligence News",
    # Asia
    "Japan FSA": "Financial Services Agency of Japan",
    "Reserve Bank of India (RBI)": "Reserve Bank of India",
    "Singapore IMDA": "Infocomm Media Development Authority of Singapore",
    "China MIIT": "Ministry of Industry and Information Technology of China",
    # Africa
    "African Union": "African Union",
    "NTRA Egypt": "National Telecom Regulatory Authority of Egypt",
    "NCC Nigeria": "Nigerian Communications Commission",
    "ICASA South Africa": "Independent Communications Authority of South Africa",
    # Middle East
    "TRA UAE": "Telecommunications and Digital Government Regulatory Authority (UAE)",
    "CITC Saudi Arabia": "Communications, Space and Technology Commission (Saudi Arabia)",
    "Qatar CRA": "Communications Regulatory Authority of Qatar",
    # Canada
    "CRTC": "Canadian Radio-television and Telecommunications Commission",
    "ISED": "Innovation, Science and Economic Development Canada",
    "Office of the Privacy Commissioner": "Office of the Privacy Commissioner of Canada",
    # Australia
    "ACMA": "Australian Communications and Media Authority",
    "OAIC": "Office of the Australian Information Commissioner",
    "NSW AI Assurance Framework": "New South Wales AI Assurance Framework",
    # China
    "CAC": "Cyberspace Administration of China",
    "Ministry of Industry and Information Technology": "Ministry of Industry and Information Technology of China",
    "Shanghai AI Regulations": "Shanghai AI Regulations",
    # India
    "MeitY": "Ministry of Electronics and Information Technology (India)",
    "TRAI": "Telecom Regulatory Authority of India",
    "NITI Aayog AI": "NITI Aayog Artificial Intelligence Initiative (India)",
    # Japan
    "MIC": "Ministry of Internal Affairs and Communications (Japan)",
    "Japan AI Principles": "Japan Social Principles of Human-Centric AI",
    # Brazil
    "ANATEL": "Agência Nacional de Telecomunicações (Brazil)",
    "MCTIC": "Ministry of Science, Technology, Innovations and Communications (Brazil)",
    "Brazil AI Law": "Brazil Artificial Intelligence Law",
    # Russia
    "Roskomnadzor": "Federal Service for Supervision of Communications, Information Technology and Mass Media (Russia)",
    "Ministry of Digital Development": "Ministry of Digital Development, Communications and Mass Media (Russia)",
    # Global
    "BIS": "Bank for International Settlements",
    "IMF": "International Monetary Fund",
    "World Bank": "World Bank",
    "OECD": "Organisation for Economic Co-operation and Development",
    "ITU": "International Telecommunication Union",
    # Technology/AI/IT/Telecom
    "IEEE Standards News": "IEEE Standards Association News",
    "ISO/IEC JTC 1/SC 42 (AI)": "ISO/IEC Joint Technical Committee 1/Subcommittee 42 on Artificial Intelligence",
    "AI Now Institute": "AI Now Institute",
    "OECD AI Policy Observatory": "OECD AI Policy Observatory",
    "International Telecommunication Union (ITU)": "International Telecommunication Union",
    "GSMA": "GSM Association",
}

# UI settings
AVATAR_IMAGES = (
    None,
    "./images/avatar.png",
)

# Default chat parameters
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_LLM_MODEL = "gpt-4.1-mini"
