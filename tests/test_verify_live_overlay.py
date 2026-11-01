from __future__ import annotations

import unittest

from scripts.verify_live_overlay import CHECKS, validate_area_explorer_bundle


class LiveOverlayVerifierTests(unittest.TestCase):
    def test_bundle_contract_accepts_dynamic_layer_ids(self) -> None:
        app = "import {createAreaExplorer} from './area-explorer.mjs';"
        explorer = """
export function createAreaExplorer(options) {
  const prefix = options.kind === 'ward' ? 'area-region' : 'neighbourhood-region';
  return { fill: `${prefix}-fill` };
}
"""

        validate_area_explorer_bundle(app, explorer)

    def test_bundle_contract_requires_app_import_and_module_export(self) -> None:
        with self.assertRaisesRegex(ValueError, 'does not import'):
            validate_area_explorer_bundle("const area = 'createAreaExplorer';", "export function createAreaExplorer() {}")
        with self.assertRaisesRegex(ValueError, 'does not export'):
            validate_area_explorer_bundle("import {createAreaExplorer} from './area-explorer.mjs';", "const area = 'createAreaExplorer';")

    def test_verifier_uses_the_app_overlay_asset_paths(self) -> None:
        paths = {path for path, _ in CHECKS}
        self.assertIn('data/scarborough-wards.geojson', paths)
        self.assertIn('data/scarborough-overlay-neighbourhoods.geojson', paths)


if __name__ == '__main__':
    unittest.main()
