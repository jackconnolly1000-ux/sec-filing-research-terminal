"""Common interpretation gates used by all three saved company downloads."""
import importlib
COMMON=(('annual_history_sha256','annual_history_view'),('guide_sha256','export_guide'),
        ('charts_sha256','core_charts'),('history_sha256','company_history'),
        ('ratios_sha256','ratio_review'),('borrowing_leases_sha256','borrowing_leases'))

def common_matches(metadata):
    return all(metadata.get(field)==importlib.import_module(module).fingerprint() for field,module in COMMON)
