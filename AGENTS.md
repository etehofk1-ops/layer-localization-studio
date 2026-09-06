# Repository working agreement

This repository contains the reusable localization workflow, not a game's patch or a landing page.

- Read README.md and skills/asset-localization/SKILL.md before production changes.
- Preserve original bytes and every generation attempt. Never overwrite an existing job, attempt ID or build revision.
- Source pixel cutout/erasure/inpainting and source alpha inheritance are outside this workflow. Local processing is for generated assets and measured parameters.
- Keep customer data, credentials, machine-specific paths and unrelated game assets out of commits. The user authorized historical Furuyoni production and successful application case studies under case-studies/furuyoni/ in this private repository; preserve their separate rights notice. Use synthetic test images under ignored jobs/ or temporary directories for automated tests.
- No automatic generation spending, game installation changes, publishing or messaging. The CLI is local and has no generation/network client.
- Do not equate structural PASS with visual fidelity, readability, in-game QA or release approval.
- Keep SKILL.md concise; schemas/examples belong in its references folder. Do not install global agents or plugins from this repository.
- Run `python -m unittest discover -s tests -v` after code changes. Add behavioral coverage for changes to file preservation, PSD composition or record integrity.
- One writer per job folder. Do not overwrite another task's work. Preserve partial failures and retry with a new revision.
