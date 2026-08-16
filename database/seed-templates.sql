-- SD-007 system templates (firm_id NULL — available to every Firm).
-- Not a Drizzle migration: seeding real data isn't schema, and Drizzle's
-- generate/migrate workflow is a pure schema diff tool (CLAUDE.md's
-- "/database — a CLI tool, not an application"). Run once by hand
-- (or after a DB reset) via:
--   docker exec -i legalaiassistant-postgres-1 psql -U legal_ai -d legal_ai_assistant < seed-templates.sql
-- Idempotent: skips insertion if a template with the same name already exists.

INSERT INTO templates (firm_id, name, description, body)
SELECT NULL, 'Non-Disclosure Agreement', 'Mutual confidentiality agreement between the Client and a counterparty.',
$body$NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of {{effective_date}} by and between {{client_name}} ("Disclosing Party") and {{counterparty_name}} ("Receiving Party"), in connection with the matter titled "{{matter_title}}".

1. CONFIDENTIAL INFORMATION. The Receiving Party agrees to hold in confidence all information disclosed by the Disclosing Party in connection with this matter, and to use it solely for the purpose of evaluating or performing that matter.

2. TERM. This Agreement shall remain in effect for {{term_years}} years from the Effective Date.

3. GOVERNING LAW. This Agreement shall be governed by the laws of {{governing_law}}.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date first written above.
$body$
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE firm_id IS NULL AND name = 'Non-Disclosure Agreement');

INSERT INTO templates (firm_id, name, description, body)
SELECT NULL, 'Demand Notice', 'A formal notice demanding action or payment from the opposing party.',
$body$DEMAND NOTICE

Date: {{effective_date}}

To: {{counterparty_name}}

Re: {{matter_title}}

This letter is sent on behalf of {{client_name}} in connection with the above-referenced matter.

You are hereby notified that {{demand_details}}.

You are required to respond within {{response_days}} days of the date of this notice, failing which further legal action may be pursued without further notice to you.

Sincerely,
{{client_name}}
$body$
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE firm_id IS NULL AND name = 'Demand Notice');
