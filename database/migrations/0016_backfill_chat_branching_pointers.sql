-- Data backfill for the chat-message branching pointers added (nullable, no
-- backfill) by migration 0015.
--
-- Before 0015 a Matter's chat was a flat list ordered by created_at. 0015
-- introduced parent_id / active_child_id (per message) and
-- matters.active_root_message_id, and the app rebuilds the active
-- conversation by walking those pointers. For any conversation that already
-- existed when 0015 ran, every pointer is NULL, so:
--   * active_path() finds no root and returns nothing, and
--   * siblings(matter, parent_id => NULL) matches EVERY message in the
--     Matter, so the "<  i/N  >" question-version switcher shows a bogus
--     count and its arrows activate unrelated messages.
--
-- A Matter needs repair when it has chat messages AND either it has no
-- active_root_message_id, or it contains an assistant message with a NULL
-- parent_id (the application code never creates one of those — it is a
-- reliable "this conversation predates 0015" marker). Such conversations
-- have no real branches, so rebuilding each as a single linear chain in
-- created_at order is lossless. Matters used only after 0015 match neither
-- condition and are left untouched.

WITH targets AS (
    SELECT m.id AS matter_id
    FROM matters m
    WHERE EXISTS (SELECT 1 FROM chat_messages c WHERE c.matter_id = m.id)
      AND (
        m.active_root_message_id IS NULL
        OR EXISTS (
            SELECT 1 FROM chat_messages a
            WHERE a.matter_id = m.id AND a.role = 'assistant' AND a.parent_id IS NULL
        )
      )
),
ordered AS (
    -- created_at is the pre-0015 ordering; id is only a deterministic
    -- tie-break for messages saved within the same clock tick.
    SELECT c.id, c.matter_id,
           ROW_NUMBER() OVER (PARTITION BY c.matter_id ORDER BY c.created_at ASC, c.id ASC) AS rn
    FROM chat_messages c
    WHERE c.matter_id IN (SELECT matter_id FROM targets)
),
relink AS (
    UPDATE chat_messages c
    SET parent_id = prev.id,
        active_child_id = nxt.id
    FROM ordered o
    LEFT JOIN ordered prev ON prev.matter_id = o.matter_id AND prev.rn = o.rn - 1
    LEFT JOIN ordered nxt  ON nxt.matter_id  = o.matter_id AND nxt.rn  = o.rn + 1
    WHERE c.id = o.id
    RETURNING c.id
)
UPDATE matters m
SET active_root_message_id = root.id
FROM (
    SELECT DISTINCT ON (o.matter_id) o.matter_id, o.id
    FROM ordered o
    ORDER BY o.matter_id, o.rn
) root
WHERE m.id = root.matter_id;
