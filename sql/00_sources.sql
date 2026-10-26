-- Raw CSVs exposed as views. Paths are relative to the repository root.
CREATE OR REPLACE VIEW members             AS SELECT * FROM read_csv_auto('data/raw/members.csv');
CREATE OR REPLACE VIEW monthly_activity    AS SELECT * FROM read_csv_auto('data/raw/monthly_activity.csv');
CREATE OR REPLACE VIEW answer_interactions AS SELECT * FROM read_csv_auto('data/raw/answer_interactions.csv');

-- Study design in one place
CREATE OR REPLACE TABLE design AS
SELECT
    DATE '2025-11-01' AS launch_month,
    DATE '2025-03-01' AS before_start,   -- "before" window: Mar to May 2025
    DATE '2025-05-01' AS before_end,
    DATE '2026-01-01' AS exposure_start, -- exposure is measured in Jan and Feb 2026
    DATE '2026-02-01' AS exposure_end,
    DATE '2026-06-01' AS after_start,    -- "after" window: Jun to Aug 2026
    DATE '2026-08-01' AS after_end,
    4                 AS min_interactions; -- interactions in the exposure window to count as "frequent"
