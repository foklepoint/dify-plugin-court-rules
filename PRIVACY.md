# Privacy Policy: Court Rules Dify Plugin

Last updated: September 30, 2026

## What the plugin does with data

- The plugin stores nothing. It has no database, cache, log file or analytics.
- It runs only when a Dify app, workflow or agent calls one of its tools.
- It sends the tool inputs to `https://api.courtrules.app` over HTTPS and returns the answer to Dify.

## What is sent to Court Rules

- Your Court Rules API key, in the `Authorization: Bearer` header.
- Tool inputs: court ids, judge slugs and names, search words, case and rule filters, years and dates.
- For Check Document Compliance: the judge slug, the document type, the page count, the word count and yes or no answers about the filing. The plugin never sends document text, files, party names or case numbers.

## What is not sent

- No data goes to any host other than `api.courtrules.app`.
- The plugin does not read Dify conversations, files, knowledge bases or user accounts.

## How Court Rules handles the data

Court Rules processes API requests under its own privacy policy: https://www.courtrules.app/privacy. That policy lists API usage data such as the endpoints called, request parameters, response codes and timestamps.

## Retention and deletion

The plugin keeps no data, so it has nothing to delete. Dify keeps the API key as the tool credential. Remove the Court Rules authorization in Dify to delete it there. Revoke the key in the Court Rules console at https://console.courtrules.app.

## Contact

api@courtrules.app
