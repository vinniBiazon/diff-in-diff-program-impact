-- Group averages per period, then three ways to read them:
--   naive_gap     : mentor_engaged vs comparison AFTER launch (what a dashboard shows)
--   baseline_gap  : the same gap BEFORE the program existed
--   did_relative  : how much more the mentor_engaged group changed, in relative terms
--                   ((after / before) for mentor_engaged) / ((after / before) for comparison) - 1
--   did_absolute  : the classic double difference in the metric's own unit
CREATE OR REPLACE TABLE group_means AS
UNPIVOT (
    SELECT study_group, period,
           COUNT(*)                    AS members,
           AVG(visits)                 AS visits,
           AVG(days_with_visit)        AS days_with_visit,
           AVG(contributions)          AS contributions,
           AVG(revenue_usd)            AS revenue_usd,
           AVG(share_of_months_active) AS share_of_months_active
    FROM member_periods
    GROUP BY 1, 2
) ON visits, days_with_visit, contributions, revenue_usd, share_of_months_active
INTO NAME metric VALUE avg_value;

CREATE OR REPLACE TABLE estimates AS
WITH w AS (
    SELECT metric,
           MAX(avg_value) FILTER (WHERE study_group = 'mentor_engaged' AND period = 'before') AS e_before,
           MAX(avg_value) FILTER (WHERE study_group = 'mentor_engaged' AND period = 'after')  AS e_after,
           MAX(avg_value) FILTER (WHERE study_group = 'comparison'     AND period = 'before') AS c_before,
           MAX(avg_value) FILTER (WHERE study_group = 'comparison'     AND period = 'after')  AS c_after
    FROM group_means
    GROUP BY 1
)
SELECT
    metric,
    e_before, e_after, c_before, c_after,
    e_after / c_after - 1                          AS naive_gap,
    e_before / c_before - 1                        AS baseline_gap,
    (e_after / e_before) / (c_after / c_before) - 1 AS did_relative,
    (e_after - e_before) - (c_after - c_before)    AS did_absolute
FROM w
ORDER BY CASE metric WHEN 'visits' THEN 1 WHEN 'days_with_visit' THEN 2 WHEN 'contributions' THEN 3
                     WHEN 'share_of_months_active' THEN 4 ELSE 5 END;
