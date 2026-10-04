-- ============================================================
-- 10_creative_ml.sql
-- Creative intelligence + predictor procedures (Python 3.11, scikit-learn pinned).
-- Code lives in src/creative_ml/ and is uploaded to @CODE_STAGE by scripts/deploy_creative_ml.py.
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE SCHEMA MARKETING_COPILOT.CREATIVE;

CREATE STAGE IF NOT EXISTS CODE_STAGE  COMMENT = 'Python handlers for creative ML procedures';
CREATE STAGE IF NOT EXISTS MODEL_STAGE COMMENT = 'joblib model bundle written by TRAIN_CTR_MODEL';

-- Step 3: attribution (net lean) with bootstrap intervals
CREATE OR REPLACE PROCEDURE COMPUTE_NET_LEAN(N_BOOT INT DEFAULT 200)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pandas', 'pyarrow', 'numpy')
IMPORTS = ('@MARKETING_COPILOT.CREATIVE.CODE_STAGE/common.py', '@MARKETING_COPILOT.CREATIVE.CODE_STAGE/net_lean.py')
HANDLER = 'net_lean.run'
COMMENT = 'Adjusted CTR lift per attribute value and stratum (synthetic data)';

-- Step 4: train baseline / Ridge / HGB / quantile models, write metrics, predictions, importances
CREATE OR REPLACE PROCEDURE TRAIN_CTR_MODEL()
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pandas', 'pyarrow', 'numpy', 'scikit-learn==1.5.2', 'joblib==1.4.2')
IMPORTS = ('@MARKETING_COPILOT.CREATIVE.CODE_STAGE/common.py', '@MARKETING_COPILOT.CREATIVE.CODE_STAGE/train_model.py')
HANDLER = 'train_model.run'
COMMENT = 'Trains CTR models on V_AD_FEATURES with a 10-week time holdout';

-- Step 4: scenario scoring for the Predictor tab
CREATE OR REPLACE PROCEDURE SCORE_AD(PAYLOAD VARIANT)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pandas', 'pyarrow', 'numpy', 'scikit-learn==1.5.2', 'joblib==1.4.2')
IMPORTS = ('@MARKETING_COPILOT.CREATIVE.CODE_STAGE/score_ad.py')
HANDLER = 'score_ad.run'
COMMENT = 'Scenario estimate of CTR with p10-p90 range and top drivers (synthetic data)';
