# Court Rules

**Author:** foklepoint
**Version:** 0.0.1
**Type:** tool
**Source repository:** https://github.com/foklepoint/dify-plugin-court-rules

Court Rules is a free reference for U.S. federal and state court rules, local rules and judge standing orders, with a deadline calculator, a REST API and a hosted MCP server. The maintainers of Court Rules publish this plugin. It gives Dify apps, workflows and agents six tools that read the Court Rules REST API.

Website: https://www.courtrules.app/
API documentation: https://docs.courtrules.app

## Tools

| Tool | What it does | Main inputs |
| --- | --- | --- |
| List Courts | Finds covered federal and state courts and returns the court id (`district_id`) | `query`, `state`, `status`, `limit` |
| List Judges | Lists the judges of one court and returns the `judge_slug` | `district_id`, `name`, `only_with_rules`, `limit` |
| Get Judge Rules | Returns the rules that apply before one judge, with source text and source URLs | `district_id`, `judge_slug`, `document_scope`, `motion_type` |
| Search Filing Rules | Searches filing rules by text, court, judge, rule type, workflow phase and case type | `q`, `district_id`, `judge_slug`, `logic_type`, `workflow_phase`, `case_type`, `limit`, `offset` |
| List Court Holidays | Lists the days a court is closed, with the official schedule URL | `district_id`, `year`, `date_from`, `date_to`, `limit` |
| Check Document Compliance | Checks page and word counts and filing facts against a judge's rules | `judge_slug`, `document_scope`, `page_count`, `word_count`, filing facts |

Every tool returns two outputs. `text` is a short digest for a model to read. `json` is the full API response for workflows.

## Setup

1. Sign in at https://console.courtrules.app with Google or email.
2. Copy your API key from the dashboard.
3. In Dify, open Tools, find Court Rules and choose Authorize.
4. Paste the key. Dify checks it with one read of the Eastern District of New York court record.

The Developer plan is free and covers all courts and judges with a per-minute rate limit. Current plans are listed at https://www.courtrules.app/api and the limits at https://docs.courtrules.app/api-reference/rate-limits.

## Usage

Agent app:

1. Add the Court Rules tools to an Agent app.
2. Ask a question that names a court or a judge.

Example questions:

- "What is the page limit for a summary judgment brief before Judge Brown in the Eastern District of New York?"
- "Which days is the Eastern District of New York closed in 2026?"
- "What courtesy copy rules apply in Cook County civil cases?"
- "Search the Los Angeles Superior Court rules for e-filing rejection and cure."

Workflow:

1. Add a Tool node and pick a Court Rules tool.
2. Map the inputs. Court ids come from List Courts and judge slugs come from List Judges.
3. Read `text` for a summary or `json` for the fields.

A typical sequence is List Courts, then List Judges, then Get Judge Rules or Search Filing Rules. Check Document Compliance runs after that for a planned filing.

## Coverage and limits

- Court ids look like `edny`, `sdny`, `il-cook-circuit` or `ca-los-angeles-superior`. Court-wide rules use the judge slug `court`.
- Check Document Compliance runs for the Eastern District of New York (`edny`) today. Other courts return an error that points to Get Judge Rules and Search Filing Rules.
- The API returns 429 with a `Retry-After` header when a rate limit is reached. The tool reports the wait time.
- Court Rules is a reference. Confirm deadlines and requirements against the court's official documents before you file.

## Data sent

The plugin stores nothing. It sends the tool inputs and your API key to `https://api.courtrules.app` over HTTPS and shows the answer. Read [PRIVACY.md](PRIVACY.md) for details.

## Development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest
pytest
```

The tests use mocked HTTP. They need no API key.

## Support

- Email: api@courtrules.app
- Issues: https://github.com/foklepoint/dify-plugin-court-rules/issues

## License

MIT. See [LICENSE](LICENSE).
