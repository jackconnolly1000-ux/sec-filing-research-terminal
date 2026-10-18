"""Rebuild all company exports from checked sources in one command, rolling back on failure.

Requires the Codex Artifact Tool runtime (CODEX_PRIMARY_RUNTIME_*), Python app dependencies,
and no network or AI service. Run: python tests/offline/build_workbooks.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cache_chart_values import patch as chart_caches
import add_workbook_hyperlinks as links

def main():
    node=os.environ['CODEX_PRIMARY_RUNTIME_NODE'];modules=os.environ['CODEX_PRIMARY_RUNTIME_NODE_MODULES']
    stems=['lly_liquidity','oracle_liquidity','vistra_liquidity']
    saved={p:p.read_bytes() for p in (ROOT/'samples').glob('*') if p.suffix in ('.xlsx','.json')}
    with tempfile.TemporaryDirectory(prefix='terminal-workbooks-') as d:
        work=Path(d);(work/'node_modules').symlink_to(modules,target_is_directory=True)
        for p in (ROOT/'tests/offline').glob('*.mjs'):shutil.copy(p,work/p.name)
        try:
            subprocess.run([node,str(work/'build_summary_template.mjs'),str(ROOT)],cwd=work,env=os.environ,check=True)
            for stem in stems:
                env=dict(os.environ,SKIP_UNCHANGED_RENDERS='1')
                subprocess.run([node,str(work/('build_'+stem+'.mjs')),str(ROOT)],cwd=work,env=env,check=True)
                path=ROOT/'samples'/f'{stem}.xlsx';chart_caches(path)
                mp=path.with_suffix('.manifest.json');manifest=json.loads(mp.read_text());manifest['workbook_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();mp.write_text(json.dumps(manifest,indent=2)+'\n')
                links.patch(stem)
            subprocess.run([sys.executable,'tests/offline/audit_release1.py'],cwd=ROOT,check=True)
            out=ROOT/'outputs/workbook-build';out.mkdir(parents=True,exist_ok=True)
            for p in work.glob('*.png'):shutil.copy(p,out/p.name)
        except BaseException:
            for p,content in saved.items():p.write_bytes(content)
            raise
    print('Three workbooks rebuilt and reconciled; prior outputs restored if any build fails.')
if __name__=='__main__':main()
