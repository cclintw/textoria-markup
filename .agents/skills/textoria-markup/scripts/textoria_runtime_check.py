#!/usr/bin/env python3
"""Check the source/reader runtime without installing anything."""
import importlib.util,json,sys
REQUIRED_PACKAGES=['charset_normalizer','bs4','jinja2','markdown_it']
def check_runtime():
    missing=[x for x in REQUIRED_PACKAGES if importlib.util.find_spec(x) is None]
    return {'python':sys.version.split()[0],'python_ok':sys.version_info>=(3,10),'required_packages':REQUIRED_PACKAGES,'missing_packages':missing,'ready':sys.version_info>=(3,10) and not missing}
if __name__=='__main__':
    result=check_runtime();print(json.dumps(result));raise SystemExit(0 if result['ready'] else 1)
