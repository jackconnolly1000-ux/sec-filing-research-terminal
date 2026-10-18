"""Shared export primitives keep styles, formulas, missingness and unrelated relationships intact."""
from datetime import date
import unittest
import xml.etree.ElementTree as ET
from xlsx_xml import column,write_cell,attach_links,NS,REL,PKG

class OpenXML(unittest.TestCase):
    def test_columns_and_cached_formulas_preserve_style_and_missing_values(self):
        self.assertEqual([column(n) for n in (1,26,27,52,53,702)],['A','Z','AA','AZ','BA','ZZ'])
        with self.assertRaises(ValueError):column(0)
        c=ET.Element('{'+NS+'}c',r='C4',s='27')
        write_cell(c,{'formula':'=A1-B1','value':-3});self.assertEqual(c.findtext('{'+NS+'}f'),'A1-B1');self.assertEqual(c.findtext('{'+NS+'}v'),'-3');self.assertEqual(c.get('s'),'27')
        write_cell(c,None);self.assertEqual(len(c),0);self.assertEqual(c.get('s'),'27')
        with self.assertRaises(ValueError):write_cell(c,float('nan'))
        write_cell(c,date(2026,6,30));self.assertTrue(float(c.findtext('{'+NS+'}v'))>46000)

    def test_source_links_preserve_chart_relationships(self):
        s=ET.Element('{'+NS+'}worksheet');ET.SubElement(s,'{'+NS+'}sheetData');ET.SubElement(s,'{'+NS+'}pageMargins')
        r=ET.Element('{'+PKG+'}Relationships');ET.SubElement(r,'{'+PKG+'}Relationship',Id='rIdChart',Type=REL+'/drawing',Target='../drawings/drawing1.xml')
        result=ET.fromstring(attach_links(s,[('A2','https://www.sec.gov/example?a=1&b=2')],ET.tostring(r)))
        self.assertEqual(len(result),2);self.assertEqual(result[0].get('Id'),'rIdChart');self.assertEqual(result[1].get('Target'),'https://www.sec.gov/example?a=1&b=2')
        self.assertLess(list(s).index(s.find('{'+NS+'}hyperlinks')),list(s).index(s.find('{'+NS+'}pageMargins')))

    def test_every_common_manifest_gate_is_required(self):
        import importlib
        from workbook_manifest import COMMON,common_matches
        metadata={key:importlib.import_module(module).fingerprint() for key,module in COMMON}
        self.assertTrue(common_matches(metadata))
        for key,_ in COMMON:
            changed=dict(metadata);changed[key]='stale';self.assertFalse(common_matches(changed),key)

    def test_deployment_refresh_cascades_to_imported_helpers_but_not_on_reruns(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from runtime_cache import refresh_modules
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/n for n in ('upstream.py','downstream.py')]
            for p in paths:p.write_text('source version one')
            modules=[SimpleNamespace(__file__=str(p),__name__=p.stem) for p in paths]
            with patch('runtime_cache.importlib.reload') as reload:
                refresh_modules(modules);self.assertEqual(reload.call_count,2)
                refresh_modules(modules);self.assertEqual(reload.call_count,2)
                paths[0].write_text('source version two')
                refresh_modules(modules);self.assertEqual(reload.call_count,4)
