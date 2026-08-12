#!/usr/bin/env python3
from __future__ import annotations
import json
from bounded_rag_review import REQUEST_SCHEMA, canonical_json, demo_records, review

request = canonical_json({"query": "How is bounded retry reviewed?", "requested_effect": "review_only", "schema": REQUEST_SCHEMA})
print(json.dumps(review(request, demo_records()), sort_keys=True))
