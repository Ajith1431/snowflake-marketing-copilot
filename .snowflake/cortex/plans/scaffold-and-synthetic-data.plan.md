# Plan: Project Scaffold and Synthetic Data Generation

## Context

- Workspace at `c:\Users\majithkumar\SnowflakeHackathon` contains only `.snowflake/cortex/plans/` and `README.md`
- Python 3.14.7 is available; faker, numpy, pandas are NOT installed yet
- `pip` must be invoked as `python -m pip` on this machine
- All 12 directories and the generator script need to be created from scratch

## Implementation Steps

### Step 1: Create folder structure

Create these 12 directories:
```
data/generators/
data/samples/
sql/ddl/
sql/dml/
sql/dynamic_tables/
semantic_models/
search/
agents/
streamlit/
tests/
docs/
.snowflake/cortex/skills/
```

### Step 2: Install Python dependencies

```powershell
python -m pip install faker numpy pandas
```

### Step 3: Write `data/generators/generate_all.py`

The script will contain these generator functions, each returning a DataFrame and saving to CSV:

1. **generate_clients()** -- 12 rows, one per brand. Hardcoded client definitions with randomized contract dates and revenue.

2. **generate_products(clients_df)** -- 40-60 rows. 3-5 products per client with industry-appropriate names (e.g., TechVista gets "CloudSync Pro", "DataVault Enterprise"). Uses a per-client product template dict.

3. **generate_channels()** -- 10 rows. Static list of the 10 specified channels.

4. **generate_audience_segments(clients_df)** -- 72-96 rows. 5-8 segments per client with realistic age_band, gender_skew, income_level, and interests_json.

5. **generate_customer_profiles(segments_df)** -- 10,000 rows. Distributed across segments proportional to estimated_size. Age drawn from segment's age_band distribution.

6. **generate_campaigns(clients_df, products_df)** -- 600 rows (50 per client). Date range 2023-01-01 to 2025-12-31. Campaign names follow patterns like "{Client} {Season} {Type} {Year}". Budget ranges $5K-$500K depending on campaign_type.

7. **generate_bridge_campaign_segment(campaigns_df, segments_df)** -- ~1500-2400 rows. 2-4 segments per campaign, allocation_pct sums to 100 via Dirichlet distribution.

8. **generate_campaign_metrics(campaigns_df, channels_df)** -- 25,000-30,000 rows. Daily grain for each campaign x 2-3 channels. Key distributions:
   - CTR: beta(2,60) scaled to 0.5%-5.0%
   - ROAS: lognormal(0.8, 0.4) clipped to 1.2-7.0
   - Conversion rate: beta(2,40) scaled to 1%-8%
   - Spend: base varies by channel (TV $2K-$10K/day, Social $100-$2K/day, Email $50-$500/day)
   - Metrics are self-consistent: clicks = impressions * ctr, conversions = clicks * conv_rate, revenue = spend * roas

9. **generate_customer_feedback(customers_df, campaigns_df)** -- 25,000 rows. Sentiment score correlated with rating. feedback_text from templates: positive ("Loved the {product} ad, very {adjective}"), neutral ("Saw the {product} campaign, it was okay"), negative ("The {product} promotion was {negative_adj}").

10. **generate_market_events()** -- 60 rows. Holidays (Christmas, Black Friday, Diwali, etc.), economic events (interest rate changes, inflation reports), competitor launches, regulatory changes, cultural moments (Super Bowl, Olympics, awards season).

11. **generate_brand_guidelines(clients_df)** -- 100-120 rows. 8-10 sections per client covering: Brand Voice, Visual Identity, Target Audience, Messaging Framework, Social Media Guidelines, Content Standards, Crisis Communication, Competitive Positioning, Campaign Approval Process, Legal Compliance. Each guideline_text is 100-200 words.

**Referential integrity enforcement:**
- All product.client_id values come from clients_df.client_id
- All segment.client_id values come from clients_df.client_id
- All campaign.client_id + product_id are valid combinations
- All bridge rows reference existing campaign_id and segment_id (same client)
- All metrics reference existing campaign_id and channel_id
- All feedback references existing customer_id and campaign_id

### Step 4: Run and verify

Execute the script, then verify:
- All 11 CSV files exist in `data/samples/`
- Row counts match targets
- Spot-check: no NULL foreign keys, CTR/ROAS/conversion_rate within specified ranges
- campaign_metrics computed columns are consistent (clicks = impressions * ctr, etc.)

## Verification

```powershell
# After running the script, verify file counts and sizes:
Get-ChildItem data/samples/*.csv | Select-Object Name, Length
# Check row counts:
python -c "import pandas as pd; import glob; [print(f'{f}: {len(pd.read_csv(f))} rows') for f in sorted(glob.glob('data/samples/*.csv'))]"
```

## Critical Files

- `data/generators/generate_all.py` -- The main generator script (~700 lines)
- `data/samples/*.csv` -- 11 output CSV files
- `docs/marketing_copilot_planning.md` -- Planning doc (to be created from earlier plan)
