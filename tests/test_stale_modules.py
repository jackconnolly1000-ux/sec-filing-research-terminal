"""A long-running Streamlit Cloud worker keeps imported modules across deploys. app.py must reload the
modules whose new names it uses, or the page fails (Oct 17, 2026: ui.inject_css read theme.FLOW_IN from an
old theme module and the live app raised AttributeError)."""
import os
import unittest

from streamlit.testing.v1 import AppTest

import theme
import ui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StaleModules(unittest.TestCase):
    def test_app_recovers_when_theme_is_an_older_version(self):
        saved = {name: getattr(theme, name) for name in ("FLOW_IN", "FLOW_OUT", "SERIES_CASH", "SERIES_BORROWING")}
        try:
            for name in saved:             # simulate the previous deploy's theme module still being loaded
                delattr(theme, name)
            app = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
            app.run()
            self.assertFalse(app.exception, [e.value for e in app.exception])
            self.assertTrue(hasattr(theme, "FLOW_IN"))
        finally:
            for name, value in saved.items():
                if not hasattr(theme, name):
                    setattr(theme, name, value)

    def test_app_recovers_when_company_history_is_an_older_version(self):
        # The annual-history PR changed company_history's checked hash; a worker still holding the old module would
        # refuse the new JSON ("History source facts changed") unless app.py reloads it
        import company_history
        saved = company_history.CHECKED_SHA256
        try:
            company_history.CHECKED_SHA256 = "69082f1c56993e848a3e358f280224f536303b9199f4ec0f57fd944a00b9184c"
            app = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
            app.run()
            for ticker in ("LLY", "ORCL", "VST"):
                app.segmented_control[0].set_value(ticker).run()
                self.assertFalse(app.exception, [e.value for e in app.exception])
                self.assertTrue(any("Five completed fiscal years" in m.value for m in app.markdown), ticker)
        finally:
            company_history.CHECKED_SHA256 = saved

    def test_every_theme_name_ui_uses_exists(self):
        import re, inspect
        used = set(re.findall(r"\bT\.([A-Z_]+)", inspect.getsource(ui)))
        self.assertEqual(sorted(n for n in used if not hasattr(theme, n)), [])


if __name__ == "__main__":
    unittest.main()
