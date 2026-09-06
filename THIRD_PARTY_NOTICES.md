# External dependencies

Dependencies are installed through pip; their source code and licenses are not relicensed by this repository.

| Dependency | Use | Upstream |
| --- | --- | --- |
| Pillow | Read PNG, measure alpha/colors, composite and compare | https://github.com/python-pillow/Pillow |
| psd-tools and its composite extras | Write and reopen raster-layer PSD, verify composition | https://github.com/psd-tools/psd-tools |
| setuptools | Python package build | https://github.com/pypa/setuptools |

Transitive dependencies retain their own licenses. Historical game-art case studies are stored separately under `case-studies/furuyoni/`; see [their rights notice](case-studies/ASSET-RIGHTS.md). Fonts, game executables, model weights, image-generation API clients and upstream agent plugin runtimes are not vendored.

API references checked during implementation:

- [psd-tools layer API](https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.api.layers.html)
- [PSDImage API](https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.html)

Installed psd-tools 1.18.0 source signatures were also inspected. Dependency pins reflect the tested local versions, not a claim that those are the newest releases.
