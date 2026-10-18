// Compatibility entry point; the old competing --charts path is retired.
import {execFileSync} from 'node:child_process';
const root=process.argv[2];if(!root||process.argv.includes('--charts'))throw Error('Use python tests/offline/build_workbooks.py; --charts is retired.');
execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['tests/offline/build_workbooks.py'],{cwd:root,stdio:'inherit'});
