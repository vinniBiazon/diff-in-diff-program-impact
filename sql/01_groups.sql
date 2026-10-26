-- Two comparable groups of FREQUENT interactors, defined in the exposure window:
--   mentor_engaged : 4+ interactions with mentor answers
--   comparison     : 4+ interactions with regular answers and none with mentor answers
-- Both groups are frequent readers; what separates them is whose answers they interact with.
-- Members must have joined before the "before" window, so both periods can be measured.
CREATE OR REPLACE TABLE exposure AS
SELECT
    ai.member_id,
    SUM(ai.interactions) FILTER (WHERE ai.answer_author = 'mentor')  AS mentor_interactions,
    SUM(ai.interactions) FILTER (WHERE ai.answer_author = 'regular') AS regular_interactions
FROM answer_interactions ai, design d
WHERE ai.month BETWEEN d.exposure_start AND d.exposure_end
GROUP BY 1;

CREATE OR REPLACE TABLE study_groups AS
SELECT
    e.member_id,
    CASE WHEN COALESCE(e.mentor_interactions, 0) >= d.min_interactions THEN 'mentor_engaged'
         ELSE 'comparison' END AS study_group
FROM exposure e
JOIN members m USING (member_id), design d
WHERE m.joined_on < d.before_start
  AND (   COALESCE(e.mentor_interactions, 0) >= d.min_interactions
       OR (COALESCE(e.mentor_interactions, 0) = 0 AND COALESCE(e.regular_interactions, 0) >= d.min_interactions));
