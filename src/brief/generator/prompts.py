GENERATE_DESCRIPTION_PROMPT = """You write agent-callable descriptions for Splunk saved searches.

You receive a structured SPL explanation (indexes, sourcetypes, fields, transformations, output shape, plain-English summary). Produce a JSON object that an AI agent can use to decide whether to call this search.

Rules:
- `description`: 80-240 characters. Lead with a verb (Returns, Counts, Detects, Surfaces, Lists). Name specific event IDs / sourcetypes / indexes from the explanation. State the canonical use case in plain English. No hedging — no "might", "possibly", "could be useful for".
- `primary_use_case`: under 120 chars. One short phrase like "credential stuffing investigation" or "endpoint forensics triage".
- `output_fields`: exact field names that appear in the result rows.
- `mitre_techniques`: list of MITRE ATT&CK technique IDs (e.g. T1110.001) ONLY for security apps and ONLY when the SPL clearly maps. Use [] when uncertain. Never put technique IDs in the prose `description`.
- `estimated_runtime`: "fast" (<10s), "medium" (10-60s), or "slow" (>60s). Use the explanation's transformations as the signal — joins, wide time windows, and missing aggregations are slow.
- `suitable_for_agent`: true only if the search is safe (no destructive commands), has bounded output, and an agent could routinely call it without unintended side effects.
- `reasoning`: under 300 chars. State why you set `suitable_for_agent` and `estimated_runtime` the way you did, and what evidence in the SPL drove it.

Return ONLY the JSON object, no preamble."""


EVALUATE_QUALITY_PROMPT = """You evaluate the quality of Splunk saved-search descriptions.

You receive the existing description text and an SPL explanation. Score the description against this rubric:

- `quality_score`: 0-10. 0 = useless. 10 = an AI agent could call this confidently from the description alone.
- `is_tautology`: true if the description merely repeats the search name without saying what it does. "auth search" describing `get_auth_events` is a tautology. "Returns count of failed Linux SSH logins" is not.
- `specifies_data_source`: true if the description names an index, sourcetype, event ID, or named data system (Sysmon, syslog, AWS CloudTrail).
- `specifies_use_case`: true if the description states when an agent should call it ("for credential stuffing investigations", "during endpoint triage").
- `actionable`: true if a calling agent could decide whether the search fits its current task using this description alone.
- `reasoning`: brief justification (under 300 chars). Reference specific words from the description.

Return ONLY the JSON object, no preamble."""
