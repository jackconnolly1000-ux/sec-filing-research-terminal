"""Completed scenario runs are immutable snapshots, separate from draft widget inputs."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import liquidity_simulation as ls


def evidence_version():
    root = Path(__file__).parent
    files = ("liquidity_simulation.py", "scenario_export.py", "scenario_state.py", "xlsx_xml.py",
             "samples/scenario_template.xlsx", "samples/scenario_template.manifest.json",
             "samples/liquidity_pilots.json", "samples/oracle_liquidity.json",
             "samples/oracle_principal.json", "samples/oracle_revolver.json")
    return hashlib.sha256(b"".join(hashlib.sha256((root / p).read_bytes()).digest() for p in files)).hexdigest()


def clear_scenario(state):
    for key in list(state):
        if key.startswith("sim_"):
            del state[key]


def reset_for_version(state, version):
    if state.get("scenario_evidence_version") != version:
        clear_scenario(state)
        state["scenario_evidence_version"] = version


def input_key(chosen, version):
    inputs, decisions, trials, seed = chosen
    payload = [version, asdict(inputs), [asdict(d) for d in decisions], trials, seed]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def calculate(chosen, uses, version):
    inputs, decisions, trials, seed = chosen
    ls.validate_inputs(inputs, seed)
    results = [(ls.simulate(inputs, d, trials, seed), d) for d in decisions]
    return {"key": input_key(chosen, version), "chosen": chosen, "results": results,
            "monthly": [(d, r, ls.monthly_path(inputs, d, trials, seed)) for r, d in results],
            "comparisons": {},
            "outside": [(d, ls.outside_use_effects(inputs, uses, d, trials, seed)) for d in decisions],
            "stability": ls.simulate(inputs, decisions[0], trials * 5, seed + 1), "exports": {}}
