"""Boundary, cache and state regressions from the October 18 audit."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from contextlib import closing
import time
import unittest
from openpyxl import load_workbook
import liquidity_simulation as ls
import scenario_export
import scenario_state
from runtime_cache import ResponseStore


class InputSafety(unittest.TestCase):
    def test_seed_rejects_negative_fractional_and_boolean(self):
        for seed in (-1, 0.5, True):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                ls.simulate(ls.oracle_inputs(), ls.oracle_decisions()[0], 10, seed)

    def test_negative_cash_uses_rejected(self):
        for capex, dividend in ((-1, 0), (0, -1)):
            with self.assertRaises(ValueError):
                ls.Decision("invalid", capex, dividend, False)
        inputs = replace(ls.oracle_inputs(), prepayments=ls.Triangular(-3, -2, -1))
        with self.assertRaises(ValueError):
            ls.simulate(inputs, ls.oracle_decisions()[0], 10)

    def test_negative_ocf_is_permitted(self):
        inputs = replace(ls.oracle_inputs(), ocf_ex_prepayments=ls.Triangular(-3, -2, -1))
        self.assertEqual(ls.simulate(inputs, ls.oracle_decisions()[0], 10)["trials"], 10)

    def test_evidence_change_resets_only_scenario(self):
        state = {"sim_seed": 7, "sim_completed": {}, "review_company": "ORCL"}
        scenario_state.reset_for_version(state, "a")
        self.assertEqual(state, {"review_company": "ORCL", "scenario_evidence_version": "a"})
        state["sim_seed"] = 9
        scenario_state.reset_for_version(state, "a")
        self.assertEqual(state["sim_seed"], 9)
        scenario_state.reset_for_version(state, "b")
        self.assertNotIn("sim_seed", state)

    def test_export_keeps_exact_prepayment_ceiling(self):
        inputs = replace(ls.oracle_inputs(), prepayments=ls.Triangular(0, 0, 2e9))
        decisions = ls.oracle_decisions()
        results = [(ls.simulate(inputs, d, 10, 7), d) for d in decisions]
        with closing(load_workbook(BytesIO(scenario_export.workbook(inputs, results, 10, 7)), data_only=True)) as book:
            self.assertEqual(book["Scenario"]["E9"].value, 2e9)


class Coordination(unittest.TestCase):
    def test_identical_requests_only_compute_once(self):
        store, calls = ResponseStore(), []
        def run(_):
            with store.request("same"):
                if store.get("same") is None:
                    calls.append(1)
                    time.sleep(0.01)
                    store["same"] = {"at": time.time(), "raw": 7}
                return store.get("same")["raw"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(list(pool.map(run, range(8))), [7] * 8)
        self.assertEqual(len(calls), 1)
        self.assertEqual(store._flights, {})

    def test_expiry_and_capacity(self):
        now = [0]
        store = ResponseStore(ttl=3, max_entries=2, clock=lambda: now[0])
        for k in range(3):
            store[k] = {"at": 0, "raw": k}
        self.assertIsNone(store.get(0))
        now[0] = 4
        self.assertIsNone(store.get(2))
