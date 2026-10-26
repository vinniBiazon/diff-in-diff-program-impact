-- One row per member and period with monthly averages. Months without any visit count
-- as zero, so a member who went quiet pulls the average down instead of disappearing.
CREATE OR REPLACE TABLE member_periods AS
WITH periods AS (
    SELECT 'before' AS period, before_start AS p_start, before_end AS p_end FROM design
    UNION ALL
    SELECT 'after', after_start, after_end FROM design
), grid AS (
    SELECT g.member_id, g.study_group, p.period, p.p_start, p.p_end,
           DATE_DIFF('month', p.p_start, p.p_end) + 1 AS n_months
    FROM study_groups g CROSS JOIN periods p
)
SELECT
    grid.member_id,
    grid.study_group,
    grid.period,
    COALESCE(SUM(a.visits), 0)          / grid.n_months AS visits,
    COALESCE(SUM(a.days_with_visit), 0) / grid.n_months AS days_with_visit,
    COALESCE(SUM(a.contributions), 0)   / grid.n_months AS contributions,
    COALESCE(SUM(a.revenue_usd), 0)     / grid.n_months AS revenue_usd,
    COUNT(a.month)                      / grid.n_months AS share_of_months_active
FROM grid
LEFT JOIN monthly_activity a
       ON a.member_id = grid.member_id
      AND a.month BETWEEN grid.p_start AND grid.p_end
GROUP BY grid.member_id, grid.study_group, grid.period, grid.n_months;
