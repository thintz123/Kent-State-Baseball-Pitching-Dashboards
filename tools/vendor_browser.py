"""Download browser libraries; record versions and retain their license notices."""
from pathlib import Path
import json
from urllib.request import urlopen

out = Path('docs/vendor')
out.mkdir(parents=True, exist_ok=True)
packages = {'jspdf': 'dist/jspdf.umd.min.js', 'html2canvas': 'dist/html2canvas.min.js', 'jszip': 'dist/jszip.min.js'}
manifest = {}
for name, asset in packages.items():
    metadata = json.load(urlopen(f'https://registry.npmjs.org/{name}/latest'))
    version = metadata['version']
    url = f'https://unpkg.com/{name}@{version}/{asset}'
    (out / f'{name}.min.js').write_bytes(urlopen(url).read())
    manifest[name] = {'version': version, 'url': url, 'license': metadata.get('license')}
    for filename in ['LICENSE', 'LICENSE.txt', 'LICENSE.markdown']:
        try:
            license_text = urlopen(f'https://unpkg.com/{name}@{version}/{filename}').read()
            (out / f'{name}.LICENSE').write_bytes(license_text)
            break
        except Exception:
            continue
    print(name, version)
url = 'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js'
(out / 'xlsx.min.js').write_bytes(urlopen(url).read())
(out / 'xlsx.LICENSE').write_bytes(urlopen('https://cdn.sheetjs.com/xlsx-0.20.3/package/LICENSE').read())
manifest['xlsx'] = {'version': '0.20.3', 'url': url, 'license': 'Apache-2.0'}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
