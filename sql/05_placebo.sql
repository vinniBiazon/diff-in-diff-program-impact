-- Placebo test: pretend the program launched in mid-2025, when it did not exist yet.
-- Compare Jan-Feb 2025 with Jul-Aug 2025 for the same two groups.
-- A method that works should find (close to) nothing here.
CREATE OR REPLACE TABLE placebo AS
WITH periods AS (
    SELECT 'before' AS period, DATE '2025-01-01' AS p_start, DATE '2025-02-01' AS p_end
    UNION ALL
    SELECT 'after',            DATE '2025-07-01',            DATE '2025-08-01'
), mp AS (
    SELECT g.study_group, p.period, g.member_id,
           COALESCE(SUM(a.visits), 0) / 2.0        AS visits,
           COALESCE(SUM(a.contributions), 0) / 2.0 AS contributions
    FROM study_groups g
    CROSS JOIN periods p
    LEFT JOIN monthly_activity a
           ON a.member_id = g.member_id AND a.month BETWEEN p.p_start AND p.p_end
    GROUP BY 1, 2, 3
), m AS (
    SELECT study_group, period, AVG(visits) AS visits, AVG(contributions) AS contributions
    FROM mp GROUP BY 1, 2
)
SELECT
    metric,
    (MAX(v) FILTER (WHERE study_group = 'mentor_engaged' AND period = 'after')
     / MAX(v) FILTER (WHERE study_group = 'mentor_engaged' AND period = 'before'))
  / (MAX(v) FILTER (WHERE study_group = 'comparison' AND period = 'after')
     / MAX(v) FILTER (WHERE study_group = 'comparison' AND period = 'before')) - 1 AS placebo_did_relative
FROM (UNPIVOT m ON visits, contributions INTO NAME metric VALUE v)
GROUP BY 1;
