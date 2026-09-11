# Public release checklist

Updated: 2026-09-11. Scope: make the existing workflow repository public after privacy and security review. Counts describe completed checklist items, not a guarantee of security.

- [x] PUB-01 Confirm repository, clean checkout, remote refs, and publication authorization. Initial HEAD: `74c075f`; one branch, four commits; private.
- [x] PUB-02 Review all reachable history, text and binary metadata, author identities, and GitHub publication surfaces. No disclosure requiring removal found in four original commits, 48 PNGs and 3 PSDs.
- [x] PUB-03 Complete source-backed security review and dependency advisory checks. Two output-path findings retained and addressed; 16 installed package versions had no OSV matches after local tool updates. See [review](security-review-2026-09-11.md).
- [x] PUB-04 Resolve both validated findings, pass independent source re-review, and clarify public documentation and separate asset rights. Original case-study bytes preserved.
- [x] PUB-05 Run behavioral tests (17 pass, one documented Windows permission skip), synthetic CLI verification (24 files, 3 PSD layers), final staged Gitleaks/privacy checks, and exact-diff review. No sensitive tracked filenames or current-text matches.
- [x] PUB-06 Push reviewed code `0b04f33`, change visibility to PUBLIC, and verify the repository API, README, security policy and original/localized images without authentication (HTTP 200). Remote main matched local HEAD. Secret scanning, push protection and private vulnerability reporting were enabled and read back.

Progress: 6/6. Next: none for this publication request. Test limitations remain documented in the review.
