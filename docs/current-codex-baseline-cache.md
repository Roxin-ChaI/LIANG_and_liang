# Current official Codex baseline cache (Phase 8F)

On 2026-09-24 the official OpenAI CDN supplied a 650,455,829-byte DMG,
SHA256 `dc872e7713711cd6b14d22bafe0c0afec6ac0524d0f03ab0ed226f4e40e5848c`.
The URL is mutable; the checksum, not the URL or filename, pins this build.
The verified DMG is retained locally at
`.cache/official-codex/ChatGPT-26.917.62051-10789.dmg`. The entire `.cache/`
tree is ignored by Git, and the official App, DMG and proprietary JavaScript
must never be committed.

The DMG passed `hdiutil verify` and was mounted **read-only**. Its App is
version `26.917.62051`, Build `10789`, Bundle ID `com.openai.codex`, Team ID
`2DC432GLL2`, arm64, Developer ID Application signed with a stapled
notarization ticket. Deep/strict `codesign`, nested-code verification and
Gatekeeper all passed in a normal macOS trust context. Hardened Runtime is
enabled; main entitlements are valid XML. The raw ASAR JSON-header hash
`3cfd8249ac8e4f99b157318543923e18ead06cbf6940e4fa77d14119a0ca579e`
matches Electron's `ElectronAsarIntegrity` metadata, while the complete
archive SHA256 is separately frozen. The existing clean-reference validator
returned `CLEAN_REFERENCE_PASS` and `zeroMutation=true`.

These facts are frozen in
[`runtime-patch/builds/10789/trusted-baseline.json`](../runtime-patch/builds/10789/trusted-baseline.json).
Run `python tools/verify_official_codex_cache.py` before each reuse. It requires
the exact size and SHA256 and refuses a symlink, missing file or unsafe path.
The cache check does not replace the original signature/Gatekeeper validation;
the pinned byte identity links the cached DMG to that completed validation.

The ordinary sandbox reported a false `codesign`/Gatekeeper failure, while
the same unchanged mounted App passed both under normal macOS trust
evaluation. This matches the Phase 8A trust-context finding; no security
setting was changed. The DMG was unmounted after validation and caching.

Source: the [official OpenAI desktop download page](https://learn.chatgpt.com/docs/app).
