-- ============================================
-- MCP Tool Stored Procedures
-- Wraps creative studio functions as Snowflake procedures
-- accessible via MCP GENERIC tool type
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARKETING_COPILOT;
USE SCHEMA SEMANTIC;
USE WAREHOUSE MARKETING_WH;

-- 1. Video Storyboard Generator
CREATE OR REPLACE PROCEDURE GENERATE_STORYBOARD(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR, CREATIVE_DIRECTION VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
import json
def run(session, client_name, product_name, objective, creative_direction):
    scenes = [
        {"scene": 1, "duration": "0-1s", "description": f"Opening hero shot -- {product_name} reveal with cinematic lighting", "camera": "Slow zoom in", "mood": "Anticipation"},
        {"scene": 2, "duration": "1-3s", "description": f"Core benefit -- {objective} message through audience connection", "camera": "Medium shot, subtle pan", "mood": "Emotional resonance"},
        {"scene": 3, "duration": "3-4s", "description": f"{product_name} in use -- lifestyle context showing aspiration", "camera": "Close up detail", "mood": "Aspiration"},
        {"scene": 4, "duration": "4-5s", "description": f"{client_name} brand end card with tagline", "camera": "Static brand frame", "mood": "Trust"}
    ]
    prompt = (
        f"5-second cinematic brand video for {product_name} by {client_name}. "
        f"Goal: {objective}. Visual: {creative_direction}. "
        f"Style: Premium brand film, smooth camera, vibrant colours. No text. No logos."
    )
    return {"scenes": scenes, "video_prompt": prompt, "duration": "5 seconds", "client": client_name, "product": product_name}
$$;

-- 2. Design System Builder
CREATE OR REPLACE PROCEDURE BUILD_DESIGN_SYSTEM(
    CLIENT_NAME VARCHAR, BRAND_COLOURS VARCHAR, TONE_KEYWORDS VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
def run(session, client_name, brand_colours, tone_keywords):
    colours = [c.strip() for c in brand_colours.split(",") if c.strip()]
    names = ["Primary", "Secondary", "Accent", "Background", "Text"]
    palette = [{"name": names[i] if i < len(names) else f"Colour {i+1}", "hex": c, "usage": f"{names[i]} elements"} for i, c in enumerate(colours[:5])]
    tones = [t.strip() for t in tone_keywords.split(",")]
    return {
        "client": client_name, "palette": palette, "tone": tones,
        "do": ["Use brand colours consistently", "Lead with benefits not features", "Show real people in real situations", "Use active voice"],
        "dont": ["Use competitor names", "Make unsubstantiated claims", "Crowd the composition", "Use generic stock imagery"]
    }
$$;

-- 3. Poster Prompt Builder
CREATE OR REPLACE PROCEDURE BUILD_POSTER_PROMPT(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR,
    TARGET_AUDIENCE VARCHAR, BRAND_COLOURS VARCHAR, TONE_KEYWORDS VARCHAR,
    CREATIVE_DIRECTION VARCHAR, EVENT_NAME VARCHAR
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
def run(session, client_name, product_name, objective, target_audience, brand_colours, tone_keywords, creative_direction, event_name):
    event_ctx = f"Event: {event_name}. " if event_name else ""
    return (
        f"Professional marketing poster for {client_name} promoting {product_name}. "
        f"Objective: {objective}. Audience: {target_audience}. "
        f"Brand colours: {brand_colours}. Tone: {tone_keywords}. "
        f"Direction: {creative_direction}. {event_ctx}"
        f"Style: Clean modern commercial advertising. Portrait orientation. No watermarks. No logos."
    )
$$;

-- 4. Audio Script Builder
CREATE OR REPLACE PROCEDURE BUILD_AUDIO_SCRIPT(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR, TONE_KEYWORDS VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
def run(session, client_name, product_name, objective, tone_keywords):
    return {
        "prompt": f"30-second script for {product_name} by {client_name}. Tone: {tone_keywords}. Goal: {objective}. Include: hook (5s), benefit (15s), emotional close (7s), CTA (3s).",
        "duration": "30 seconds",
        "format": "Radio / Digital Audio"
    }
$$;
