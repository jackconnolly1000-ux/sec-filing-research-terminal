"""Stable source-fact identity; conflicting observations must not silently overwrite a fact."""
import hashlib
import json


def fact_id(fact):
    fields = {k: fact.get(k) for k in ("accession", "tag", "context_id", "period_start", "period_end", "unit")}
    fields["dimensions"] = sorted(tuple(x) for x in fact.get("dimensions", []))
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:24]


class FactRegistry:
    def __init__(self):
        self.facts = {}

    def add(self, fact):
        key = fact_id(fact)
        if key in self.facts and self.facts[key]["value"] != fact["value"]:
            raise ValueError("Conflicting values for one source fact: " + key)
        self.facts.setdefault(key, dict(fact, fact_id=key))
        return key
