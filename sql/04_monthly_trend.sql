-- Monthly average visits per member for each group, across the whole history.
-- Used to check the key assumption: before launch, both groups should move in parallel.
CREATE OR REPLACE TABLE monthly_trend AS
WITH months AS (
    SELECT DISTINCT month FROM monthly_activity
), grid AS (
    SELECT g.member_id, g.study_group, m.month
    FROM study_groups g CROSS JOIN months m
)
SELECT
    grid.study_group,
    grid.month,
    AVG(COALESCE(a.visits, 0)) AS avg_visits
FROM grid
LEFT JOIN monthly_activity a USING (member_id, month)
GROUP BY 1, 2
ORDER BY 1, 2;
