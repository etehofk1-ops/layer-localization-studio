# Security policy

## Supported version

Use version 0.1.1 or a later reviewed version. Version 0.1.0 did not consistently validate persisted job identifiers or resolved output destinations. See the [2026-09-11 review](docs/security-review-2026-09-11.md).

## Local trust boundary

This is a local CLI with the filesystem permissions of the account running it. It has no server, authentication service, image-generation client, automatic publisher or billing client.

- Review job folders and every input path in third-party JSON before processing them. Input PNGs, references and processing recipes may be selected from outside the JSON directory. Recipes are copied, never executed, but can still contain private data.
- Derived output paths must resolve within the selected job. Persisted asset identifiers are validated again when loaded. Output destinations are checked before any build directory is created.
- Use one writer per job. Path validation does not provide a sandbox or protection against concurrent filesystem changes by another process.
- Images are parsed by Pillow and psd-tools. Use current supported dependencies and reasonable input sizes. There is no total memory, JSON-size or layer-count quota for an untrusted multi-user service.
- Manifests detect changes against local records; they are not signed authenticity certificates. Structural PASS does not approve visual quality, game integration or release.

## Privacy before sharing

Originals and generated references retain their bytes and may retain embedded metadata. Prompts, notes, analysis, reviewer fields and additional layer metadata are not automatically redacted. Inspect them before sharing or committing an archive. The default ignore rules exclude working folders, but selected case-study media are deliberately tracked.

Never include credentials, private customer files, personal contact information or machine-specific paths in public reports. Keep game-asset rights separate from the code license.

## Reporting a vulnerability

Private vulnerability reporting is enabled for this repository. Use [Security → Report a vulnerability](https://github.com/etehofk1-ops/layer-localization-studio/security/advisories/new). Include the affected version, a minimal synthetic example, expected behavior and actual behavior. Do not publish credentials or private game/customer files in an issue. If private reporting is unavailable, request a private reporting channel from the repository owner without posting sensitive details.
