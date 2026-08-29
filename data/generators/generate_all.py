"""
Synthetic Data Generator for NovaSpark Agency - Marketing Co-Pilot & Pitch Engine
Generates 11 CSV datasets for 12 client brands across diverse industries.
"""

import os
import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Client definitions
# ---------------------------------------------------------------------------
CLIENT_DEFS = [
    {"client_id": "C001", "client_name": "LuminaRetail", "industry": "Retail", "region": "North America"},
    {"client_id": "C002", "client_name": "TechVista", "industry": "Technology", "region": "Global"},
    {"client_id": "C003", "client_name": "CareWell", "industry": "Healthcare", "region": "North America"},
    {"client_id": "C004", "client_name": "FinEdge", "industry": "Finance", "region": "Europe"},
    {"client_id": "C005", "client_name": "PureLife", "industry": "CPG", "region": "North America"},
    {"client_id": "C006", "client_name": "DriveMax", "industry": "Automotive", "region": "Global"},
    {"client_id": "C007", "client_name": "Wanderlux", "industry": "Travel", "region": "Europe"},
    {"client_id": "C008", "client_name": "ConnectSphere", "industry": "Telecom", "region": "Asia Pacific"},
    {"client_id": "C009", "client_name": "FlavorCo", "industry": "Food & Beverage", "region": "North America"},
    {"client_id": "C010", "client_name": "UrbanThread", "industry": "Fashion", "region": "Europe"},
    {"client_id": "C011", "client_name": "MediaPulse", "industry": "Media & Entertainment", "region": "Global"},
    {"client_id": "C012", "client_name": "GreenCore", "industry": "Energy", "region": "North America"},
]

# Products per client (industry-specific)
PRODUCT_TEMPLATES = {
    "C001": [("LR-HomeEssentials", "Home Goods", "mid"), ("LR-FashionForward", "Apparel", "premium"), ("LR-DailyDeals", "Discount", "budget"), ("LR-KidsCorner", "Children", "mid")],
    "C002": [("TV-CloudSync Pro", "SaaS", "premium"), ("TV-DataVault", "Storage", "mid"), ("TV-SecureNet", "Security", "premium"), ("TV-DevKit Starter", "Developer Tools", "budget"), ("TV-AI Insights", "Analytics", "premium")],
    "C003": [("CW-VitaBoost", "Supplements", "mid"), ("CW-TeleCare Plus", "Telehealth", "premium"), ("CW-FitTrack", "Wearables", "mid"), ("CW-MindCalm", "Mental Health", "budget")],
    "C004": [("FE-WealthGuard", "Investment", "premium"), ("FE-QuickLoan", "Lending", "mid"), ("FE-PaySwift", "Payments", "budget"), ("FE-InsureMe", "Insurance", "mid"), ("FE-CryptoEdge", "Digital Assets", "premium")],
    "C005": [("PL-NaturalGlow", "Skincare", "mid"), ("PL-CleanHome", "Cleaning", "budget"), ("PL-BabyPure", "Baby Care", "mid"), ("PL-FreshBite", "Snacks", "budget")],
    "C006": [("DM-ElectraDrive", "Electric Vehicle", "premium"), ("DM-UrbanCruiser", "SUV", "mid"), ("DM-SpeedStar", "Sports Car", "premium"), ("DM-EcoFleet", "Commercial", "mid")],
    "C007": [("WL-LuxuryEscapes", "Premium Travel", "premium"), ("WL-AdventureSeeker", "Adventure", "mid"), ("WL-FamilyFun", "Family Packages", "mid"), ("WL-BusinessClass", "Corporate Travel", "premium"), ("WL-BudgetWander", "Economy", "budget")],
    "C008": [("CS-UltraConnect 5G", "Mobile Plans", "premium"), ("CS-HomeStream", "Broadband", "mid"), ("CS-BizLink", "Enterprise", "premium"), ("CS-PrepaidFlex", "Prepaid", "budget")],
    "C009": [("FC-CraftBrew", "Beverages", "mid"), ("FC-OrganicBites", "Organic Food", "premium"), ("FC-SnackAttack", "Snacks", "budget"), ("FC-MealPrep Pro", "Ready Meals", "mid")],
    "C010": [("UT-StreetStyle", "Streetwear", "mid"), ("UT-LuxeLine", "Luxury", "premium"), ("UT-ActiveWear", "Athleisure", "mid"), ("UT-EcoThread", "Sustainable", "mid"), ("UT-Essentials", "Basics", "budget")],
    "C011": [("MP-StreamNow", "Streaming", "mid"), ("MP-GameVerse", "Gaming", "mid"), ("MP-NewsFlash", "News", "budget"), ("MP-PodcastHub", "Podcasts", "budget")],
    "C012": [("GC-SolarMax", "Solar Panels", "premium"), ("GC-WindForce", "Wind Energy", "premium"), ("GC-GreenHome", "Home Energy", "mid"), ("GC-EcoBattery", "Storage", "mid")],
}

CHANNEL_DEFS = [
    ("CH01", "Instagram", "Social"),
    ("CH02", "YouTube", "Video"),
    ("CH03", "Google Search", "Search"),
    ("CH04", "Facebook", "Social"),
    ("CH05", "LinkedIn", "Social"),
    ("CH06", "TikTok", "Social"),
    ("CH07", "Email", "Direct"),
    ("CH08", "Programmatic Display", "Display"),
    ("CH09", "TV", "Traditional"),
    ("CH10", "Out-of-Home", "Traditional"),
]

SEGMENT_TEMPLATES = {
    "Retail": [
        ("Budget Shoppers", "18-34", "Female-leaning", "Low", ["deals", "coupons", "fast fashion"]),
        ("Premium Buyers", "35-54", "Balanced", "High", ["luxury", "quality", "brands"]),
        ("Online-First Millennials", "25-39", "Balanced", "Medium", ["ecommerce", "mobile shopping", "reviews"]),
        ("Family Shoppers", "30-49", "Female-leaning", "Medium", ["kids", "home", "value packs"]),
        ("Loyalty Members", "25-54", "Balanced", "Medium", ["rewards", "repeat purchases", "exclusives"]),
        ("Gen Z Trendsetters", "18-24", "Balanced", "Low-Medium", ["social media", "sustainability", "viral products"]),
    ],
    "Technology": [
        ("Enterprise IT Leaders", "35-54", "Male-leaning", "High", ["cloud", "security", "enterprise"]),
        ("Startup Founders", "25-39", "Male-leaning", "Medium-High", ["SaaS", "growth", "automation"]),
        ("Developer Community", "22-39", "Male-leaning", "Medium", ["APIs", "open source", "devtools"]),
        ("SMB Decision Makers", "30-49", "Balanced", "Medium", ["cost-effective", "scalable", "integration"]),
        ("Tech Enthusiasts", "18-34", "Male-leaning", "Medium", ["gadgets", "innovation", "early adopter"]),
    ],
    "Healthcare": [
        ("Health-Conscious Millennials", "25-39", "Female-leaning", "Medium", ["wellness", "fitness", "organic"]),
        ("Senior Caregivers", "40-65", "Female-leaning", "Medium", ["eldercare", "telehealth", "insurance"]),
        ("Fitness Enthusiasts", "18-34", "Balanced", "Medium", ["gym", "wearables", "nutrition"]),
        ("Chronic Care Patients", "45-65", "Balanced", "Medium-High", ["medication", "monitoring", "support"]),
        ("New Parents", "25-39", "Female-leaning", "Medium", ["baby health", "pediatrics", "safety"]),
        ("Mental Health Seekers", "18-44", "Balanced", "Medium", ["therapy", "meditation", "stress relief"]),
    ],
    "Finance": [
        ("Young Investors", "22-34", "Male-leaning", "Medium", ["stocks", "crypto", "apps"]),
        ("High-Net-Worth Individuals", "40-65", "Male-leaning", "High", ["wealth management", "estate planning", "private banking"]),
        ("Small Business Owners", "30-54", "Balanced", "Medium-High", ["loans", "payments", "accounting"]),
        ("First-Time Homebuyers", "25-39", "Balanced", "Medium", ["mortgage", "savings", "credit score"]),
        ("Retirees", "55-70", "Balanced", "Medium-High", ["pension", "annuities", "low risk"]),
        ("Digital-Native Bankers", "18-29", "Balanced", "Low-Medium", ["mobile banking", "neobank", "instant transfers"]),
        ("Insurance Seekers", "30-49", "Balanced", "Medium", ["life insurance", "health coverage", "family protection"]),
    ],
    "CPG": [
        ("Eco-Conscious Consumers", "25-44", "Female-leaning", "Medium-High", ["organic", "sustainable", "natural"]),
        ("Value Seekers", "18-54", "Balanced", "Low-Medium", ["bulk", "coupons", "store brand"]),
        ("New Moms", "25-39", "Female-leaning", "Medium", ["baby products", "safety", "gentle"]),
        ("Health & Beauty Enthusiasts", "18-39", "Female-leaning", "Medium", ["skincare", "wellness", "clean beauty"]),
        ("Household Managers", "30-54", "Female-leaning", "Medium", ["cleaning", "organization", "family"]),
    ],
    "Automotive": [
        ("EV Early Adopters", "30-49", "Male-leaning", "High", ["electric", "sustainability", "tech"]),
        ("Luxury Car Enthusiasts", "35-59", "Male-leaning", "High", ["performance", "prestige", "craftsmanship"]),
        ("Family Vehicle Buyers", "30-49", "Balanced", "Medium", ["safety", "space", "reliability"]),
        ("First-Time Car Buyers", "22-30", "Balanced", "Medium", ["affordable", "financing", "compact"]),
        ("Fleet Managers", "35-54", "Male-leaning", "Medium-High", ["commercial", "efficiency", "TCO"]),
        ("Performance Seekers", "25-44", "Male-leaning", "Medium-High", ["speed", "horsepower", "racing"]),
    ],
    "Travel": [
        ("Luxury Travelers", "35-59", "Balanced", "High", ["five-star", "exclusive", "concierge"]),
        ("Backpackers", "18-30", "Balanced", "Low", ["hostels", "adventure", "budget"]),
        ("Family Vacationers", "30-49", "Balanced", "Medium", ["kid-friendly", "resorts", "packages"]),
        ("Business Travelers", "30-54", "Male-leaning", "High", ["lounges", "efficiency", "loyalty programs"]),
        ("Adventure Seekers", "22-39", "Balanced", "Medium", ["hiking", "extreme sports", "nature"]),
        ("Cultural Explorers", "25-54", "Balanced", "Medium-High", ["museums", "local cuisine", "history"]),
        ("Digital Nomads", "25-39", "Balanced", "Medium", ["coworking", "long stays", "wifi"]),
    ],
    "Telecom": [
        ("Heavy Data Users", "18-34", "Male-leaning", "Medium", ["streaming", "gaming", "unlimited"]),
        ("Family Plan Seekers", "30-49", "Balanced", "Medium", ["shared plans", "parental controls", "value"]),
        ("Business Enterprises", "30-54", "Male-leaning", "High", ["SLA", "dedicated lines", "security"]),
        ("Prepaid Customers", "18-29", "Balanced", "Low", ["flexibility", "no contract", "affordable"]),
        ("Rural Connectivity", "25-65", "Balanced", "Medium", ["coverage", "reliability", "fixed wireless"]),
        ("Tech-Savvy Upgraders", "22-39", "Balanced", "Medium-High", ["5G", "latest phones", "speed"]),
    ],
    "Food & Beverage": [
        ("Health-Conscious Eaters", "25-44", "Balanced", "Medium-High", ["organic", "plant-based", "low sugar"]),
        ("Foodies", "22-39", "Balanced", "Medium", ["gourmet", "craft", "artisanal"]),
        ("Busy Professionals", "25-44", "Balanced", "Medium", ["meal prep", "quick meals", "convenience"]),
        ("Parents with Kids", "30-44", "Female-leaning", "Medium", ["kid-friendly", "nutritious", "snacks"]),
        ("Snack Lovers", "18-34", "Balanced", "Low-Medium", ["chips", "candy", "impulse buys"]),
        ("Craft Beer & Wine", "25-49", "Male-leaning", "Medium-High", ["microbrewery", "wine club", "tasting"]),
    ],
    "Fashion": [
        ("Luxury Fashion Buyers", "25-49", "Female-leaning", "High", ["designer", "runway", "exclusive"]),
        ("Streetwear Enthusiasts", "18-29", "Balanced", "Medium", ["sneakers", "hype drops", "urban"]),
        ("Sustainable Fashion Advocates", "22-39", "Female-leaning", "Medium", ["ethical", "recycled", "slow fashion"]),
        ("Athleisure Fans", "22-39", "Balanced", "Medium", ["yoga", "running", "comfortable"]),
        ("Basics Buyers", "25-54", "Balanced", "Low-Medium", ["essentials", "minimalist", "wardrobe staples"]),
        ("Occasion Shoppers", "25-44", "Female-leaning", "Medium-High", ["wedding", "formal", "seasonal"]),
    ],
    "Media & Entertainment": [
        ("Binge Watchers", "18-34", "Balanced", "Medium", ["streaming", "series", "movies"]),
        ("Gamers", "16-34", "Male-leaning", "Medium", ["console", "PC", "esports"]),
        ("Podcast Listeners", "25-44", "Balanced", "Medium", ["true crime", "business", "comedy"]),
        ("News Junkies", "30-65", "Balanced", "Medium-High", ["breaking news", "analysis", "politics"]),
        ("Music Streamers", "18-34", "Balanced", "Low-Medium", ["playlists", "concerts", "new releases"]),
        ("Sports Fans", "18-54", "Male-leaning", "Medium", ["live sports", "fantasy", "highlights"]),
    ],
    "Energy": [
        ("Homeowners Going Solar", "35-59", "Balanced", "Medium-High", ["solar panels", "tax credits", "savings"]),
        ("Eco-Warriors", "22-39", "Balanced", "Medium", ["renewable", "carbon neutral", "activism"]),
        ("Commercial Property Managers", "35-54", "Male-leaning", "High", ["energy efficiency", "HVAC", "smart building"]),
        ("EV Charging Adopters", "30-49", "Balanced", "Medium-High", ["home charging", "fast charging", "network"]),
        ("Off-Grid Enthusiasts", "30-54", "Balanced", "Medium", ["batteries", "independence", "rural"]),
    ],
}

CAMPAIGN_TYPES = ["awareness", "consideration", "conversion", "retention"]
CAMPAIGN_OBJECTIVES = {
    "awareness": ["Increase brand visibility", "Launch new product", "Build market presence", "Expand brand recognition"],
    "consideration": ["Drive website traffic", "Generate leads", "Boost engagement", "Educate prospects"],
    "conversion": ["Increase online sales", "Drive store visits", "Boost sign-ups", "Maximize ROAS"],
    "retention": ["Reduce churn", "Increase repeat purchases", "Build loyalty program", "Win back lapsed customers"],
}
SEASONS = ["Q1 New Year", "Q1 Spring", "Q2 Summer", "Q2 Midyear", "Q3 Back-to-School", "Q3 Fall", "Q4 Holiday", "Q4 Year-End"]

FEEDBACK_POSITIVE = [
    "Really loved the {product} campaign, felt very authentic and engaging.",
    "The {product} ads caught my attention immediately. Great visuals!",
    "Impressive messaging for {product}. Made me want to learn more.",
    "The {product} promotion was exactly what I was looking for. Purchased right away.",
    "{product} branding is top-notch. Shared it with friends.",
    "Saw the {product} ad on {channel} and it really resonated with me.",
    "Great experience with {product}. The campaign messaging was spot on.",
    "The creative direction for {product} was fresh and memorable.",
    "{product} campaign felt personal and relevant to my needs.",
    "Excellent targeting - the {product} ad appeared at the perfect time.",
]
FEEDBACK_NEUTRAL = [
    "Noticed the {product} ad but didn't feel compelled to act.",
    "The {product} campaign was decent, nothing extraordinary though.",
    "Saw {product} mentioned on {channel}. It was fine.",
    "The {product} messaging was clear but could be more compelling.",
    "{product} campaign was okay. I've seen better from competitors.",
    "Not sure what made {product} different from alternatives.",
    "The {product} ad was professional but didn't stand out.",
    "Received the {product} email, skimmed it briefly.",
]
FEEDBACK_NEGATIVE = [
    "The {product} ad was annoying and too frequent.",
    "Not impressed with the {product} campaign. Felt generic.",
    "{product} promotion was misleading. Expected better.",
    "Couldn't relate to the {product} messaging at all.",
    "The {product} ad disrupted my browsing experience negatively.",
    "Poor targeting for {product}. Completely irrelevant to me.",
    "{product} campaign felt outdated compared to competitors.",
    "Too many {product} ads on {channel}. Consider reducing frequency.",
]

GUIDELINE_SECTIONS = [
    "Brand Voice & Tone",
    "Visual Identity Standards",
    "Target Audience Personas",
    "Messaging Framework",
    "Social Media Guidelines",
    "Content Standards & Quality",
    "Crisis Communication Protocol",
    "Competitive Positioning",
    "Campaign Approval Process",
    "Legal & Compliance Requirements",
]

TONE_KEYWORDS_BY_INDUSTRY = {
    "Retail": ["friendly", "approachable", "value-driven", "inclusive", "exciting"],
    "Technology": ["innovative", "trustworthy", "intelligent", "forward-thinking", "precise"],
    "Healthcare": ["compassionate", "trustworthy", "empowering", "professional", "caring"],
    "Finance": ["authoritative", "secure", "transparent", "empowering", "sophisticated"],
    "CPG": ["natural", "cheerful", "reliable", "family-friendly", "wholesome"],
    "Automotive": ["powerful", "confident", "sleek", "adventurous", "premium"],
    "Travel": ["inspiring", "adventurous", "luxurious", "welcoming", "transformative"],
    "Telecom": ["connected", "reliable", "modern", "simple", "empowering"],
    "Food & Beverage": ["flavorful", "authentic", "fresh", "joyful", "crafted"],
    "Fashion": ["bold", "elegant", "expressive", "contemporary", "aspirational"],
    "Media & Entertainment": ["exciting", "immersive", "dynamic", "creative", "engaging"],
    "Energy": ["sustainable", "innovative", "responsible", "future-focused", "empowering"],
}

COLOR_PALETTES = {
    "Retail": "#FF6B35, #004E89, #FFFFFF, #1A1A2E",
    "Technology": "#0077B6, #00B4D8, #023E8A, #CAF0F8",
    "Healthcare": "#2D6A4F, #52B788, #FFFFFF, #D8F3DC",
    "Finance": "#1B1464, #0652DD, #C0C0C0, #F5F5F5",
    "CPG": "#F77F00, #FCBF49, #EAE2B7, #003049",
    "Automotive": "#2B2D42, #EF233C, #8D99AE, #EDF2F4",
    "Travel": "#006D77, #83C5BE, #FFDDD2, #E29578",
    "Telecom": "#7209B7, #3A0CA3, #4361EE, #4CC9F0",
    "Food & Beverage": "#D62828, #F77F00, #FCBF49, #003049",
    "Fashion": "#000000, #FFFFFF, #C9B037, #8B7355",
    "Media & Entertainment": "#FF006E, #8338EC, #3A86FF, #FFBE0B",
    "Energy": "#2D6A4F, #40916C, #95D5B2, #D8F3DC",
}


def _date_range(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    return start, end


def generate_clients():
    rows = []
    for c in CLIENT_DEFS:
        rows.append({
            "client_id": c["client_id"],
            "client_name": c["client_name"],
            "industry": c["industry"],
            "region": c["region"],
            "annual_revenue_usd": round(random.uniform(50_000_000, 5_000_000_000), -5),
            "contract_start_date": fake.date_between(start_date="-4y", end_date="-1y").isoformat(),
            "primary_contact": fake.name(),
            "status": "active",
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "clients.csv"), index=False)
    return df


def generate_products(clients_df):
    rows = []
    pid = 1
    for _, client in clients_df.iterrows():
        cid = client["client_id"]
        for pname, cat, tier in PRODUCT_TEMPLATES[cid]:
            rows.append({
                "product_id": f"P{pid:04d}",
                "client_id": cid,
                "product_name": pname,
                "category": cat,
                "launch_date": fake.date_between(start_date="-3y", end_date="today").isoformat(),
                "price_tier": tier,
                "description": fake.paragraph(nb_sentences=3),
            })
            pid += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "products.csv"), index=False)
    return df


def generate_channels():
    rows = [{"channel_id": cid, "channel_name": cn, "channel_type": ct} for cid, cn, ct in CHANNEL_DEFS]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "channels.csv"), index=False)
    return df


def generate_audience_segments(clients_df):
    rows = []
    sid = 1
    for _, client in clients_df.iterrows():
        industry = client["industry"]
        cid = client["client_id"]
        templates = SEGMENT_TEMPLATES.get(industry, SEGMENT_TEMPLATES["Retail"])
        for seg_name, age_band, gender_skew, income, interests in templates:
            rows.append({
                "segment_id": f"S{sid:04d}",
                "client_id": cid,
                "segment_name": seg_name,
                "age_band": age_band,
                "gender_skew": gender_skew,
                "income_level": income,
                "interests_json": json.dumps(interests),
                "estimated_size": random.randint(50_000, 2_000_000),
            })
            sid += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "audience_segments.csv"), index=False)
    return df


def generate_customer_profiles(segments_df):
    rows = []
    cust_id = 1
    total_target = 10_000
    seg_sizes = segments_df["estimated_size"].values.astype(float)
    proportions = seg_sizes / seg_sizes.sum()
    counts = np.round(proportions * total_target).astype(int)
    diff = total_target - counts.sum()
    if diff != 0:
        counts[0] += diff

    regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
    channels = ["organic_search", "paid_social", "email", "referral", "direct", "paid_search"]

    for i, (_, seg) in enumerate(segments_df.iterrows()):
        age_band = seg["age_band"]
        parts = age_band.replace("+", "").split("-")
        age_min, age_max = int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0]) + 20
        gender_skew = seg["gender_skew"]
        for _ in range(int(counts[i])):
            if "Female" in gender_skew:
                gender = random.choices(["Female", "Male", "Non-binary"], weights=[0.6, 0.35, 0.05])[0]
            elif "Male" in gender_skew:
                gender = random.choices(["Male", "Female", "Non-binary"], weights=[0.6, 0.35, 0.05])[0]
            else:
                gender = random.choices(["Male", "Female", "Non-binary"], weights=[0.47, 0.47, 0.06])[0]
            rows.append({
                "customer_id": f"CU{cust_id:06d}",
                "segment_id": seg["segment_id"],
                "client_id": seg["client_id"],
                "age": random.randint(age_min, age_max),
                "gender": gender,
                "geo_region": random.choice(regions),
                "lifetime_value_usd": round(random.uniform(50, 15000), 2),
                "acquisition_channel": random.choice(channels),
                "join_date": fake.date_between(start_date="-3y", end_date="today").isoformat(),
            })
            cust_id += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "customer_profiles.csv"), index=False)
    return df


def generate_campaigns(clients_df, products_df):
    rows = []
    camp_id = 1
    date_start, date_end = _date_range("2023-01-01", "2025-12-31")

    budget_ranges = {
        "awareness": (50_000, 500_000),
        "consideration": (20_000, 200_000),
        "conversion": (10_000, 150_000),
        "retention": (5_000, 80_000),
    }
    statuses_pool = ["completed", "completed", "completed", "active", "active", "planned"]

    for _, client in clients_df.iterrows():
        cid = client["client_id"]
        client_products = products_df[products_df["client_id"] == cid]["product_id"].tolist()
        for i in range(50):
            ctype = random.choice(CAMPAIGN_TYPES)
            objective = random.choice(CAMPAIGN_OBJECTIVES[ctype])
            season = SEASONS[i % len(SEASONS)]
            year = random.choice([2023, 2024, 2025])
            start = fake.date_between_dates(
                date_start=datetime(year, 1, 1),
                date_end=datetime(year, 11, 1),
            )
            duration = random.randint(14, 90)
            end = start + timedelta(days=duration)
            if end > date_end.date():
                end = date_end.date()
            bmin, bmax = budget_ranges[ctype]
            rows.append({
                "campaign_id": f"CAM{camp_id:04d}",
                "client_id": cid,
                "product_id": random.choice(client_products),
                "campaign_name": f"{client['client_name']} {season} {ctype.title()} {year}",
                "campaign_type": ctype,
                "objective": objective,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "total_budget_usd": round(random.uniform(bmin, bmax), -2),
                "status": random.choice(statuses_pool),
            })
            camp_id += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "campaigns.csv"), index=False)
    return df


def generate_bridge_campaign_segment(campaigns_df, segments_df):
    rows = []
    for _, camp in campaigns_df.iterrows():
        cid = camp["client_id"]
        client_segs = segments_df[segments_df["client_id"] == cid]["segment_id"].tolist()
        n_segs = random.randint(2, min(4, len(client_segs)))
        chosen = random.sample(client_segs, n_segs)
        raw = np.random.dirichlet(np.ones(n_segs))
        pcts = np.round(raw * 100, 1)
        pcts[-1] = round(100 - pcts[:-1].sum(), 1)
        for seg_id, pct in zip(chosen, pcts):
            rows.append({
                "campaign_id": camp["campaign_id"],
                "segment_id": seg_id,
                "allocation_pct": float(pct),
            })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "bridge_campaign_segment.csv"), index=False)
    return df


def generate_campaign_metrics(campaigns_df, channels_df):
    rows = []
    mid = 1

    channel_spend_base = {
        "CH01": (100, 1500), "CH02": (200, 2000), "CH03": (300, 3000),
        "CH04": (100, 1200), "CH05": (150, 1800), "CH06": (80, 1000),
        "CH07": (50, 500), "CH08": (200, 2500), "CH09": (2000, 10000),
        "CH10": (500, 5000),
    }
    channel_ids = channels_df["channel_id"].tolist()

    for _, camp in campaigns_df.iterrows():
        start = datetime.strptime(camp["start_date"], "%Y-%m-%d")
        end = datetime.strptime(camp["end_date"], "%Y-%m-%d")
        n_days = (end - start).days + 1
        if n_days <= 0:
            continue

        n_channels = random.randint(2, 3)
        selected_channels = random.sample(channel_ids, n_channels)
        total_budget = camp["total_budget_usd"]
        daily_budget_per_channel = total_budget / (n_days * n_channels)

        for ch_id in selected_channels:
            spend_min, spend_max = channel_spend_base[ch_id]
            base_ctr = np.random.beta(2, 60)
            base_ctr = np.clip(base_ctr, 0.005, 0.05)
            base_conv_rate = np.random.beta(2, 40)
            base_conv_rate = np.clip(base_conv_rate, 0.01, 0.08)
            base_roas = np.random.lognormal(0.8, 0.4)
            base_roas = np.clip(base_roas, 1.2, 7.0)

            for day_offset in range(n_days):
                date = start + timedelta(days=day_offset)
                dow_factor = 1.2 if date.weekday() < 5 else 0.8
                noise = np.random.normal(1.0, 0.1)

                spend = np.clip(
                    daily_budget_per_channel * dow_factor * noise,
                    spend_min * 0.5, spend_max * 1.5
                )
                spend = round(spend, 2)

                ctr = np.clip(base_ctr * np.random.normal(1.0, 0.15), 0.005, 0.05)
                impressions = int(spend / np.clip(np.random.uniform(0.002, 0.02), 0.001, 0.1))
                clicks = max(1, int(impressions * ctr))
                conv_rate = np.clip(base_conv_rate * np.random.normal(1.0, 0.15), 0.01, 0.08)
                conversions = max(0, int(clicks * conv_rate))
                roas = np.clip(base_roas * np.random.normal(1.0, 0.1), 1.2, 7.0)
                revenue = round(spend * roas, 2)

                actual_ctr = round(clicks / max(impressions, 1), 6)
                actual_conv_rate = round(conversions / max(clicks, 1), 6)
                actual_cpc = round(spend / max(clicks, 1), 2)

                rows.append({
                    "metric_id": f"M{mid:07d}",
                    "campaign_id": camp["campaign_id"],
                    "channel_id": ch_id,
                    "date": date.strftime("%Y-%m-%d"),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "spend_usd": spend,
                    "revenue_usd": revenue,
                    "ctr": actual_ctr,
                    "roas": round(roas, 4),
                    "cpc": actual_cpc,
                    "conversion_rate": actual_conv_rate,
                })
                mid += 1

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "campaign_metrics.csv"), index=False)
    return df


def generate_customer_feedback(customers_df, campaigns_df, products_df):
    rows = []
    fid = 1
    target = 25_000
    feedback_channels = ["email", "social_media", "app_review", "survey", "customer_support", "website"]
    product_map = dict(zip(products_df["product_id"], products_df["product_name"]))
    channel_names = [c[1] for c in CHANNEL_DEFS]

    camp_product_map = dict(zip(campaigns_df["campaign_id"], campaigns_df["product_id"]))
    camp_client_map = dict(zip(campaigns_df["campaign_id"], campaigns_df["client_id"]))
    customer_client_map = dict(zip(customers_df["customer_id"], customers_df["client_id"]))

    customer_ids = customers_df["customer_id"].tolist()
    campaign_ids = campaigns_df["campaign_id"].tolist()

    while fid <= target:
        cust_id = random.choice(customer_ids)
        cust_client = customer_client_map[cust_id]
        client_campaigns = [c for c in campaign_ids if camp_client_map[c] == cust_client]
        if not client_campaigns:
            continue
        camp_id = random.choice(client_campaigns)
        prod_id = camp_product_map[camp_id]
        prod_name = product_map.get(prod_id, "Product")
        channel = random.choice(channel_names)

        sentiment = np.random.normal(0.2, 0.4)
        sentiment = np.clip(sentiment, -1.0, 1.0)

        if sentiment > 0.3:
            template = random.choice(FEEDBACK_POSITIVE)
            rating = random.choices([4, 5], weights=[0.3, 0.7])[0]
        elif sentiment < -0.2:
            template = random.choice(FEEDBACK_NEGATIVE)
            rating = random.choices([1, 2], weights=[0.4, 0.6])[0]
        else:
            template = random.choice(FEEDBACK_NEUTRAL)
            rating = random.choice([2, 3, 4])

        text = template.format(product=prod_name, channel=channel)

        rows.append({
            "feedback_id": f"FB{fid:06d}",
            "customer_id": cust_id,
            "campaign_id": camp_id,
            "feedback_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
            "sentiment_score": round(float(sentiment), 4),
            "rating": rating,
            "feedback_text": text,
            "feedback_channel": random.choice(feedback_channels),
        })
        fid += 1

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "customer_feedback.csv"), index=False)
    return df


def generate_market_events():
    events = [
        # Holidays
        ("holiday", "New Year's Day", "Global", "2023-01-01", "2023-01-02", "medium", "New Year celebrations drive retail and travel spending spikes globally.", "Retail,Travel,Food & Beverage"),
        ("holiday", "Valentine's Day", "Global", "2023-02-14", "2023-02-14", "medium", "Consumer spending on gifts, dining, and experiences increases significantly.", "Retail,Food & Beverage,Fashion"),
        ("holiday", "Easter Weekend", "North America", "2023-04-07", "2023-04-09", "medium", "Family-focused spending on food, travel, and gifts.", "Retail,Food & Beverage,Travel"),
        ("holiday", "Diwali", "Asia Pacific", "2023-11-12", "2023-11-14", "high", "Major consumer spending event across South Asia covering electronics, gold, clothing, and sweets.", "Retail,Fashion,Technology"),
        ("holiday", "Christmas Season", "Global", "2023-12-01", "2023-12-31", "high", "Peak retail spending season with major e-commerce and in-store promotions.", "Retail,CPG,Fashion,Technology"),
        ("holiday", "Black Friday / Cyber Monday", "North America", "2023-11-24", "2023-11-27", "high", "Largest shopping weekend of the year with deep discounts across all categories.", "Retail,Technology,Fashion,CPG"),
        ("holiday", "Chinese New Year", "Asia Pacific", "2024-02-10", "2024-02-17", "high", "Extended holiday period with major consumer spending in APAC markets.", "Retail,Travel,Food & Beverage"),
        ("holiday", "Mother's Day", "North America", "2024-05-12", "2024-05-12", "medium", "Gift-giving occasion boosting retail, floral, dining, and spa industries.", "Retail,Food & Beverage,Healthcare"),
        ("holiday", "Summer Solstice Sales", "Europe", "2024-06-21", "2024-06-30", "low", "European summer sales season begins with outdoor and travel promotions.", "Fashion,Travel,Retail"),
        ("holiday", "Thanksgiving", "North America", "2024-11-28", "2024-11-28", "medium", "Family gatherings drive food and beverage sales, precedes Black Friday.", "Food & Beverage,Retail"),
        ("holiday", "New Year 2025", "Global", "2025-01-01", "2025-01-02", "medium", "New Year resolutions drive fitness, health, and self-improvement spending.", "Healthcare,Retail,Technology"),
        ("holiday", "Ramadan", "Middle East & Africa", "2025-03-01", "2025-03-30", "high", "Month-long observance with increased evening consumer activity and charitable giving.", "Food & Beverage,Retail,Fashion"),
        ("holiday", "Independence Day", "North America", "2024-07-04", "2024-07-04", "low", "Outdoor celebrations, barbecue season, and patriotic merchandise.", "Food & Beverage,Retail"),
        ("holiday", "Halloween", "North America", "2024-10-31", "2024-10-31", "medium", "Costume, candy, and decoration spending plus themed marketing campaigns.", "Retail,Food & Beverage,Media & Entertainment"),
        ("holiday", "Singles Day 11.11", "Asia Pacific", "2024-11-11", "2024-11-11", "high", "World's largest online shopping event originating from China.", "Retail,Technology,Fashion"),
        # Economic events
        ("economic", "Fed Interest Rate Hike Q1 2023", "North America", "2023-02-01", "2023-02-01", "high", "Federal Reserve raises interest rates, impacting consumer borrowing and spending patterns.", "Finance,Automotive,Retail"),
        ("economic", "EU Inflation Peak", "Europe", "2023-03-15", "2023-06-30", "high", "Eurozone inflation reaches peak levels, consumer confidence drops significantly.", "Finance,Retail,CPG,Energy"),
        ("economic", "US Consumer Confidence Rebound", "North America", "2023-09-01", "2023-12-31", "medium", "Consumer confidence index rises, signaling increased willingness to spend.", "Retail,Automotive,Travel"),
        ("economic", "Global Supply Chain Recovery", "Global", "2024-01-01", "2024-06-30", "medium", "Post-pandemic supply chain normalization reduces costs and improves availability.", "Technology,Automotive,CPG,Retail"),
        ("economic", "AI Investment Boom", "Global", "2024-03-01", "2024-12-31", "high", "Massive investment in AI technologies reshapes enterprise and consumer tech markets.", "Technology,Media & Entertainment,Finance"),
        ("economic", "Oil Price Surge", "Global", "2024-06-01", "2024-08-31", "medium", "Rising oil prices impact energy costs and consumer transportation spending.", "Energy,Automotive,Travel"),
        ("economic", "Housing Market Cooldown", "North America", "2024-09-01", "2025-03-31", "medium", "Mortgage rates remain elevated, slowing housing market and related spending.", "Finance,Retail"),
        ("economic", "Green Energy Tax Credits Extended", "North America", "2025-01-15", "2025-12-31", "high", "US government extends renewable energy tax credits boosting solar and EV adoption.", "Energy,Automotive"),
        ("economic", "APAC GDP Growth Acceleration", "Asia Pacific", "2025-04-01", "2025-12-31", "medium", "Strong GDP growth in Southeast Asia creates new consumer markets.", "Telecom,Technology,Retail"),
        ("economic", "Crypto Market Rally", "Global", "2024-11-01", "2025-03-31", "medium", "Cryptocurrency markets surge, driving fintech adoption and digital asset interest.", "Finance,Technology"),
        # Competitor launches
        ("competitor_launch", "Rival Retail Chain Digital Overhaul", "North America", "2023-03-01", "2023-03-15", "medium", "Major competitor launches redesigned e-commerce platform with AI recommendations.", "Retail"),
        ("competitor_launch", "New EV Model by Competitor", "Global", "2023-06-01", "2023-06-15", "high", "Leading competitor unveils affordable EV targeting mass market segment.", "Automotive"),
        ("competitor_launch", "Streaming Wars: New Platform Launch", "Global", "2023-09-15", "2023-09-30", "high", "Major tech company enters streaming market with aggressive pricing and exclusive content.", "Media & Entertainment"),
        ("competitor_launch", "Competitor Telehealth Expansion", "North America", "2024-01-10", "2024-01-31", "medium", "Healthcare competitor expands telehealth services to 20 new states.", "Healthcare"),
        ("competitor_launch", "FinTech Super App Launch", "Europe", "2024-04-01", "2024-04-15", "high", "European fintech launches all-in-one financial super app with banking, investing, and insurance.", "Finance"),
        ("competitor_launch", "Fast Fashion Brand Goes Sustainable", "Global", "2024-07-01", "2024-07-31", "medium", "Major fast fashion brand announces full sustainability pivot with recycled materials.", "Fashion"),
        ("competitor_launch", "Competitor 5G Home Internet", "North America", "2024-10-01", "2024-10-15", "medium", "Telecom rival launches unlimited 5G home internet at disruptive price point.", "Telecom"),
        ("competitor_launch", "Plant-Based Protein Mainstream Push", "North America", "2025-02-01", "2025-02-28", "medium", "Food competitor launches plant-based line in all major grocery chains.", "Food & Beverage,CPG"),
        ("competitor_launch", "Competitor Solar-as-a-Service", "North America", "2025-05-01", "2025-05-15", "medium", "Energy competitor launches zero-down solar leasing program.", "Energy"),
        ("competitor_launch", "Luxury Travel NFT Experiences", "Global", "2025-03-15", "2025-04-15", "low", "Travel competitor offers blockchain-verified exclusive destination experiences.", "Travel"),
        # Regulatory changes
        ("regulatory", "GDPR Enforcement Tightening", "Europe", "2023-01-15", "2023-12-31", "high", "EU tightens GDPR enforcement with larger fines for data privacy violations in advertising.", "Technology,Telecom,Retail"),
        ("regulatory", "FDA New Supplement Labeling Rules", "North America", "2023-05-01", "2023-12-31", "medium", "FDA introduces stricter labeling requirements for health supplements and wellness products.", "Healthcare,CPG"),
        ("regulatory", "Digital Services Act Implementation", "Europe", "2024-02-17", "2024-12-31", "high", "EU DSA takes full effect requiring platforms to increase ad transparency and content moderation.", "Technology,Media & Entertainment"),
        ("regulatory", "California Privacy Rights Act Update", "North America", "2024-07-01", "2024-12-31", "medium", "CPRA amendments restrict third-party data sharing for targeted advertising.", "Technology,Retail,Finance"),
        ("regulatory", "EV Emission Standards Tightened", "Global", "2024-09-01", "2025-12-31", "high", "New global emission standards accelerate transition to electric vehicles.", "Automotive,Energy"),
        ("regulatory", "AI Transparency Act", "Europe", "2025-03-01", "2025-12-31", "high", "EU mandates AI transparency in consumer-facing applications including ad targeting.", "Technology,Finance,Healthcare"),
        ("regulatory", "Sugar Tax Expansion", "Europe", "2025-01-01", "2025-12-31", "medium", "Multiple European countries expand sugar tax to more beverage and snack categories.", "Food & Beverage,CPG"),
        ("regulatory", "Cross-Border Data Flow Agreement", "Global", "2025-06-01", "2025-12-31", "medium", "New international data flow framework eases compliance for global advertising campaigns.", "Technology,Telecom"),
        # Cultural moments
        ("cultural", "Super Bowl LVII", "North America", "2023-02-12", "2023-02-12", "high", "Most-watched US sporting event. Premium ad slots and massive social media engagement.", "Media & Entertainment,Food & Beverage,Automotive"),
        ("cultural", "FIFA Women's World Cup", "Global", "2023-07-20", "2023-08-20", "high", "Global sporting event driving women's sports marketing and brand sponsorship opportunities.", "Fashion,CPG,Telecom"),
        ("cultural", "Met Gala", "North America", "2024-05-06", "2024-05-06", "medium", "High-profile fashion event generating massive social media buzz and luxury brand visibility.", "Fashion,Media & Entertainment"),
        ("cultural", "Paris Olympics 2024", "Global", "2024-07-26", "2024-08-11", "high", "Global event with massive advertising opportunities across all media channels.", "Automotive,Technology,Fashion,Food & Beverage"),
        ("cultural", "Grammy Awards", "Global", "2024-02-04", "2024-02-04", "medium", "Music industry's biggest night driving entertainment and fashion conversations.", "Media & Entertainment,Fashion"),
        ("cultural", "Coachella Music Festival", "North America", "2024-04-12", "2024-04-21", "medium", "Major cultural moment for youth marketing, fashion collaborations, and brand activations.", "Fashion,Food & Beverage,Technology"),
        ("cultural", "Back to School Season", "North America", "2024-08-01", "2024-09-15", "medium", "Major retail season for technology, clothing, and supplies.", "Retail,Technology,Fashion"),
        ("cultural", "World Cup 2026 Qualifiers Buzz", "Global", "2025-03-01", "2025-06-30", "medium", "Anticipation for 2026 World Cup drives sports marketing and sponsorship deals.", "Media & Entertainment,Telecom,Food & Beverage"),
        ("cultural", "Earth Day Awareness Campaign", "Global", "2025-04-22", "2025-04-22", "medium", "Sustainability-focused marketing moment for eco-friendly brands and green initiatives.", "Energy,CPG,Fashion"),
        ("cultural", "Oscar Awards Ceremony", "Global", "2025-03-02", "2025-03-02", "medium", "Film industry's premier event driving entertainment marketing and red carpet fashion.", "Media & Entertainment,Fashion"),
    ]

    rows = []
    for i, (etype, ename, region, sdate, edate, impact, desc, industries) in enumerate(events, 1):
        rows.append({
            "event_id": f"EV{i:03d}",
            "event_type": etype,
            "event_name": ename,
            "region": region,
            "start_date": sdate,
            "end_date": edate,
            "impact_level": impact,
            "description": desc,
            "affected_industries": industries,
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "market_events.csv"), index=False)
    return df


def _generate_guideline_text(client_name, industry, section):
    texts = {
        "Brand Voice & Tone": (
            f"{client_name} communicates with a voice that is {', '.join(TONE_KEYWORDS_BY_INDUSTRY.get(industry, ['professional'])[:3])}. "
            f"Every piece of content should reflect our commitment to excellence in the {industry.lower()} sector. "
            f"We speak directly to our audience as trusted advisors, not as distant corporations. "
            f"Our tone adapts to the platform -- more casual on social media, more authoritative in thought leadership -- "
            f"but always maintains the core brand personality. Avoid jargon unless speaking to industry professionals. "
            f"Humor is welcome when appropriate but should never undermine credibility. "
            f"All communications should empower the reader to take confident action."
        ),
        "Visual Identity Standards": (
            f"The {client_name} visual identity uses the primary color palette of {COLOR_PALETTES.get(industry, '#000000, #FFFFFF')}. "
            f"Logo placement must maintain a minimum clear space equal to the height of the logomark on all sides. "
            f"Photography should feature real people in authentic settings that reflect our {industry.lower()} audience. "
            f"Avoid stock photos that feel staged or overly corporate. "
            f"Typography uses a modern sans-serif for headlines and a clean serif for body text. "
            f"All digital assets must meet WCAG 2.1 AA accessibility standards for contrast ratios. "
            f"Infographics and data visualizations should use the secondary palette for chart elements."
        ),
        "Target Audience Personas": (
            f"{client_name} targets a diverse range of consumers within the {industry.lower()} vertical. "
            f"Our primary audience includes decision-makers aged 25-54 who value quality and innovation. "
            f"Secondary audiences include younger digital-native consumers (18-24) who discover brands through social platforms. "
            f"All messaging should consider the cultural diversity of our audience across different regions. "
            f"Personas should be refreshed quarterly based on campaign performance data and market research. "
            f"Avoid assumptions about audience preferences -- let data drive persona refinement. "
            f"Each campaign brief must identify at least two target personas with specific needs and motivations."
        ),
        "Messaging Framework": (
            f"The {client_name} messaging hierarchy follows: Brand Promise > Category Message > Product Message > Call to Action. "
            f"Our brand promise centers on delivering exceptional value in the {industry.lower()} space. "
            f"Key differentiators include innovation, reliability, and customer-centricity. "
            f"Product messaging should lead with benefits, not features. "
            f"Every campaign must include a clear, measurable call to action aligned with the funnel stage. "
            f"A/B test all headlines and key messages before scaling campaigns. "
            f"Competitive claims must be substantiated with data and approved by legal before publication."
        ),
        "Social Media Guidelines": (
            f"{client_name} maintains active presence across Instagram, Facebook, LinkedIn, TikTok, and YouTube. "
            f"Post frequency: Instagram 4-5x/week, LinkedIn 3x/week, TikTok 5-7x/week, Facebook 3-4x/week. "
            f"User-generated content is encouraged and should be reshared with proper attribution. "
            f"Response time for comments and DMs should not exceed 2 hours during business hours. "
            f"Hashtag strategy: 3-5 branded hashtags plus 5-10 relevant trending tags per post. "
            f"Paid social budgets should allocate 60% to prospecting and 40% to retargeting. "
            f"All influencer partnerships require prior brand approval and must include proper disclosure."
        ),
        "Content Standards & Quality": (
            f"All content produced for {client_name} must pass a quality checklist before publication. "
            f"Written content should maintain a Flesch reading ease score of 60-70 for general audiences. "
            f"Video content should capture attention in the first 3 seconds and include captions for accessibility. "
            f"Blog posts and articles should be 800-1500 words with proper SEO optimization including meta descriptions. "
            f"All statistics and claims must be sourced from reputable, recent (within 2 years) publications. "
            f"Visual assets must be provided in multiple formats for different platforms and aspect ratios. "
            f"Content calendars should be planned 4-6 weeks in advance with flexibility for real-time marketing."
        ),
        "Crisis Communication Protocol": (
            f"In the event of a brand crisis affecting {client_name}, all scheduled content must be paused immediately. "
            f"The crisis communication team includes the Account Director, PR Lead, Legal Counsel, and Client CMO. "
            f"Initial response must be issued within 4 hours of incident identification across all active channels. "
            f"Messaging should be empathetic, transparent, and factual -- avoid speculation or blame. "
            f"Monitor social media sentiment in real-time during crisis periods using our listening tools. "
            f"Post-crisis analysis must be conducted within 7 days including sentiment recovery tracking. "
            f"Maintain a pre-approved crisis response template library updated quarterly for common scenarios."
        ),
        "Competitive Positioning": (
            f"{client_name} positions itself as a leader in the {industry.lower()} sector through innovation and customer focus. "
            f"Competitive analysis should be conducted monthly tracking key rivals' messaging, pricing, and market share. "
            f"Never disparage competitors directly in any public-facing content -- focus on our strengths instead. "
            f"Differentiation points should be data-backed and aligned with customer pain points discovered in research. "
            f"Win/loss analysis from sales teams should inform quarterly messaging updates. "
            f"Share of voice targets: aim for top-3 position in organic search for primary category keywords. "
            f"Monitor competitor ad spend and creative direction using industry intelligence tools."
        ),
        "Campaign Approval Process": (
            f"All {client_name} campaigns follow a three-stage approval process: Internal Review, Client Review, Legal Review. "
            f"Internal review covers creative quality, brand alignment, and strategic fit -- allow 3 business days. "
            f"Client review includes the Marketing Director and Brand Manager -- allow 5 business days. "
            f"Legal review covers regulatory compliance, trademark usage, and claim substantiation -- allow 3 business days. "
            f"Revisions cycle back to the previous stage for re-approval before advancing. "
            f"Emergency campaigns (responding to events or competitors) follow an expedited 24-hour approval track. "
            f"All approved assets are archived in the digital asset management system with approval metadata."
        ),
        "Legal & Compliance Requirements": (
            f"All {client_name} marketing materials must comply with regional advertising standards and regulations. "
            f"Data collection for campaigns must adhere to GDPR (EU), CCPA (California), and relevant local privacy laws. "
            f"Testimonials and endorsements must be genuine and include proper FTC disclosure language. "
            f"Contest and sweepstakes promotions require legal review for compliance with state-by-state regulations. "
            f"Environmental and health claims must be substantiated by third-party certifications or scientific evidence. "
            f"Age-gated content (alcohol, gambling, certain health products) must use platform-level age restrictions. "
            f"All data retention policies must be documented and communicated to consumers at point of collection."
        ),
    }
    return texts.get(section, f"Guidelines for {section} at {client_name} in the {industry} industry. "
                     f"Follow best practices and maintain brand consistency across all touchpoints.")


def generate_brand_guidelines(clients_df):
    rows = []
    gid = 1
    for _, client in clients_df.iterrows():
        cid = client["client_id"]
        cname = client["client_name"]
        industry = client["industry"]
        n_sections = random.randint(8, 10)
        chosen_sections = random.sample(GUIDELINE_SECTIONS, n_sections)
        tone_kw = TONE_KEYWORDS_BY_INDUSTRY.get(industry, ["professional", "clear", "trustworthy"])

        for section in chosen_sections:
            text = _generate_guideline_text(cname, industry, section)
            dos = json.dumps(random.sample([
                "Use active voice", "Include data points", "Feature real customers",
                "Be culturally sensitive", "Maintain brand colors", "Use approved fonts",
                "Include CTAs", "Optimize for mobile", "Test before scaling",
                "Personalize when possible", "Cite credible sources", "Follow SEO best practices",
            ], 4))
            donts = json.dumps(random.sample([
                "Use competitor names negatively", "Make unsubstantiated claims",
                "Use stock photos", "Ignore accessibility standards",
                "Post without approval", "Use off-brand colors",
                "Overcomplicate messaging", "Ignore cultural sensitivities",
                "Skip legal review", "Use excessive jargon", "Neglect mobile formatting",
            ], 4))
            rows.append({
                "guideline_id": f"BG{gid:04d}",
                "client_id": cid,
                "section_title": section,
                "guideline_text": text,
                "dos": dos,
                "donts": donts,
                "tone_keywords": json.dumps(tone_kw),
                "color_palette": COLOR_PALETTES.get(industry, "#000000, #FFFFFF"),
                "created_date": fake.date_between(start_date="-2y", end_date="-6m").isoformat(),
            })
            gid += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "brand_guidelines.csv"), index=False)
    return df


def main():
    print("=" * 60)
    print("NovaSpark Agency - Synthetic Data Generator")
    print("=" * 60)

    print("\n[1/11] Generating clients...")
    clients = generate_clients()

    print("[2/11] Generating products...")
    products = generate_products(clients)

    print("[3/11] Generating channels...")
    channels = generate_channels()

    print("[4/11] Generating audience segments...")
    segments = generate_audience_segments(clients)

    print("[5/11] Generating customer profiles...")
    customers = generate_customer_profiles(segments)

    print("[6/11] Generating campaigns...")
    campaigns = generate_campaigns(clients, products)

    print("[7/11] Generating bridge_campaign_segment...")
    bridge = generate_bridge_campaign_segment(campaigns, segments)

    print("[8/11] Generating campaign metrics (this may take a moment)...")
    metrics = generate_campaign_metrics(campaigns, channels)

    print("[9/11] Generating customer feedback...")
    feedback = generate_customer_feedback(customers, campaigns, products)

    print("[10/11] Generating market events...")
    events = generate_market_events()

    print("[11/11] Generating brand guidelines...")
    guidelines = generate_brand_guidelines(clients)

    print("\n" + "=" * 60)
    print("GENERATION COMPLETE - Summary")
    print("=" * 60)
    datasets = {
        "clients.csv": clients,
        "products.csv": products,
        "channels.csv": channels,
        "audience_segments.csv": segments,
        "customer_profiles.csv": customers,
        "campaigns.csv": campaigns,
        "bridge_campaign_segment.csv": bridge,
        "campaign_metrics.csv": metrics,
        "customer_feedback.csv": feedback,
        "market_events.csv": events,
        "brand_guidelines.csv": guidelines,
    }
    total = 0
    for name, df in datasets.items():
        n = len(df)
        total += n
        print(f"  {name:<35s} {n:>8,d} rows")
    print(f"  {'TOTAL':<35s} {total:>8,d} rows")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
