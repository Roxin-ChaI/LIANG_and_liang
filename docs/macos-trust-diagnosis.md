# macOS Code Signing Trust Diagnosis

> Read-only Phase 8A evidence. No trust setting, keychain, App bundle,
> Gatekeeper policy, or security service was modified.

## Decision

- Classification: `TRUST_ENVIRONMENT_HEALTHY`
- Phase 8 decision: `STRICT_TRUST_GATE_USABLE`
- Strict trust gate usable: `true`
- Degraded gate safe to consider: `false`

## Phase 8 recovery observation

Phase 8 previously observed `CSSMERR_TP_NOT_TRUSTED` for Calculator and a
strict-verification failure for ChatGPT while commands ran inside a restricted
execution sandbox. During the approved read-only Phase 8A system diagnostic,
Calculator, TextEdit, the installed Build 9922 App, and the checksum-verified
official Build 9922 DMG all passed deep/strict verification. Their designated
requirements parsed, Gatekeeper accepted them, and their extracted certificate
chains passed `security verify-cert -p codeSign`.

The same unchanged installed App still produces a false negative when strict
verification is repeated inside the restricted command sandbox; its four
frozen critical hashes remain identical. The system `trustd` and `securityd`
services are running, and no error/fault record appeared in the bounded
ten-minute trust log. The evidence therefore identifies execution-context
restriction, not a persistent macOS trust regression or App-specific failure.
Phase 8 should retain strict trust validation and execute that read-only gate
in an approved unsandboxed context; a degraded gate is neither needed nor
authorized by this result.

## Official source and unchanged installed App

The official CDN download was verified before read-only mounting: size
`645200049` bytes, SHA256
`f4bc8e95f921f45c3f1d1891ead21eafdbe8e40612eb34cf0be173988c1996dd`,
and `hdiutil verify` PASS. Its Build `9922`, version `26.915.31945`,
`com.openai.codex` bundle ID, and ASAR SHA256
`1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`
match the frozen trusted baseline. It was unmounted and the DMG was removed
after inspection.

The installed App's Info.plist, executable, ASAR, and CodeResources SHA256
remain, respectively, `c2fb3359c596b749c548766c6a9b5a643511be08f43a98504de2a5586a385626`,
`dfe5654498e939d355702fa66e6e2400e55ec0ade61048e19e264f4bdc70b847`,
`1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`,
and `f5cf6ea3e1e015083237f9f6fab76dd5b37e34c94eaa503e0395c8d2b71a9328`.
The local clock was plausible and all extracted certificate validity periods
include the observation time. No independent network time synchronization
was performed.

## System context

- Current time: `2026-09-23T01:37:51.709304+08:00`
- UTC offset: `+0800`
- Clock plausible: `true`
- sw_vers: `ProductName:		macOS; ProductVersion:		27.0; BuildVersion:		26A428`
- Architecture: `arm64`

## App evidence

| Target | Structural | Trust | Requirement | Gatekeeper | ASAR |
| --- | --- | --- | --- | --- | --- |
| Calculator | STRUCTURAL_SIGNATURE_INTACT | TRUST_EVALUATION_PASS | PASS | ACCEPTED | N/A |
| TextEdit | STRUCTURAL_SIGNATURE_INTACT | TRUST_EVALUATION_PASS | PASS | ACCEPTED | N/A |
| Installed ChatGPT | STRUCTURAL_SIGNATURE_INTACT | TRUST_EVALUATION_PASS | PASS | ACCEPTED | PASS |
| Official clean ChatGPT | STRUCTURAL_SIGNATURE_INTACT | TRUST_EVALUATION_PASS | PASS | ACCEPTED | PASS |

## Detailed evidence

```json
{
  "apps": [
    {
      "certificateChain": {
        "output": "...certificate verification successful.\n---\nCertificate chain\n 0: macOS Software Signing\n    <cert(0x1010a0340) s: macOS Software Signing i: Apple Code Signing Certification Authority>\n    Not Before: Mar 30, 2026 16:34\n    Not After : Apr 27, 2027 19:29\n 1: Apple Code Signing Certification Authority\n    <cert(0x1010a0b40) s: Apple Code Signing Certification Authority i: Apple Root CA>\n    Not Before: Oct 18, 2017 17:41\n    Not After : Oct 16, 2030 00:00\n 2: Apple Root CA\n    <cert(0x1010a1380) s: Apple Root CA i: Apple Root CA>\n    Not Before: Apr 25, 2006 21:40\n    Not After : Feb 9, 2035 21:40\n\n---\nTrust evaluation results\n{\n    RevocationInfo =     (\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n        }\n    );\n    TrustEvaluationDate = \"2026-09-22 17:37:55 +0000\";\n    TrustEvaluationID = \"26B9E5C1-79ED-46A3-98BF-BC6F6DE4F985\";\n    TrustResultDetails =     (\n                {\n        },\n                {\n        },\n                {\n        }\n    );\n    TrustResultValue = 4;\n}",
        "returncode": 0,
        "status": "SUCCESS"
      },
      "certificates": [
        {
          "dateValidity": "VALID",
          "index": 0,
          "issuer": "CN=Apple Code Signing Certification Authority, OU=Certification Authority, O=Apple Inc., C=US",
          "notAfter": "Apr 27 19:29:51 2027 GMT",
          "notBefore": "Mar 30 16:34:05 2026 GMT",
          "parseReturncode": 0,
          "serial": "2E17A0A889A8FE49",
          "sha256Fingerprint": "1E:E9:D4:5F:25:11:1C:92:4A:A3:AD:69:F3:FF:FE:5D:A5:AC:36:91:BB:B2:A1:A4:8D:85:FA:D1:86:3E:AD:E1",
          "subject": "CN=macOS Software Signing, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 1,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Oct 16 00:00:00 2030 GMT",
          "notBefore": "Oct 18 17:41:25 2017 GMT",
          "parseReturncode": 0,
          "serial": "038A771EDF341786",
          "sha256Fingerprint": "76:84:3E:4C:6E:3A:CB:21:61:34:A5:7B:A8:AF:F5:12:E3:94:67:2B:39:66:B9:96:DA:80:F0:09:EE:7B:46:45",
          "subject": "CN=Apple Code Signing Certification Authority, OU=Certification Authority, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 2,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Feb  9 21:40:36 2035 GMT",
          "notBefore": "Apr 25 21:40:36 2006 GMT",
          "parseReturncode": 0,
          "serial": "02",
          "sha256Fingerprint": "B0:B1:73:0E:CB:C7:FF:45:05:14:2C:49:F1:29:5E:6E:DA:6B:CA:ED:7E:2C:68:C5:BE:91:B5:A1:10:01:F0:24",
          "subject": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA"
        }
      ],
      "designatedRequirement": {
        "output": "designated => identifier \"com.apple.calculator\" and anchor apple\n\nExecutable=/System/Applications/Calculator.app/Contents/MacOS/Calculator",
        "parseable": true,
        "returncode": 0
      },
      "details": {
        "output": "Executable=/System/Applications/Calculator.app/Contents/MacOS/Calculator\nIdentifier=com.apple.calculator\nFormat=app bundle with Mach-O universal (arm64e arm64e.x1)\nCodeDirectory v=20400 size=3629 flags=0x0(none) hashes=103+7 location=embedded\nPlatform identifier=26\nVersionPlatform=1\nVersionMin=1769472\nVersionSDK=1769472\nHash type=sha256 size=32\nCandidateCDHash sha256=e0ee8b423ba2f2e8980cd9610e01dd2d21497c76\nCandidateCDHashFull sha256=e0ee8b423ba2f2e8980cd9610e01dd2d21497c7625e2f0f087440023dd82777f\nHash choices=sha256\nCMSDigest=e0ee8b423ba2f2e8980cd9610e01dd2d21497c7625e2f0f087440023dd82777f\nCMSDigestType=2\nExecutable Segment base=0\nExecutable Segment limit=1310720\nExecutable Segment flags=0x1\nPage size=16384\nCDHash=e0ee8b423ba2f2e8980cd9610e01dd2d21497c76\nSignature size=4202\nAuthority=macOS Software Signing\nAuthority=Apple Code Signing Certification Authority\nAuthority=Apple Root CA\nSigned Time=Aug 9, 2026 at 11:50:01\nInfo.plist entries=35\nTeamIdentifier=not set\nSealed Resources version=2 rules=2 files=0\nInternal requirements count=1 size=68\nTotal signatures=1\nChosen signature=1",
        "returncode": 0
      },
      "gatekeeper": {
        "output": "/System/Applications/Calculator.app: accepted\nsource=Apple System",
        "returncode": 0,
        "status": "ACCEPTED"
      },
      "kind": "system",
      "name": "Calculator",
      "path": "/System/Applications/Calculator.app",
      "present": true,
      "verifyVerbose4": {
        "output": "/System/Applications/Calculator.app: valid on disk\n/System/Applications/Calculator.app: satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      },
      "verifyVerbose6": {
        "output": "/System/Applications/Calculator.app: valid on disk\n/System/Applications/Calculator.app: satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      }
    },
    {
      "certificateChain": {
        "output": "...certificate verification successful.\n---\nCertificate chain\n 0: macOS Software Signing\n    <cert(0x1034a79d0) s: macOS Software Signing i: Apple Code Signing Certification Authority>\n    Not Before: Mar 30, 2026 16:34\n    Not After : Apr 27, 2027 19:29\n 1: Apple Code Signing Certification Authority\n    <cert(0x1034a81d0) s: Apple Code Signing Certification Authority i: Apple Root CA>\n    Not Before: Oct 18, 2017 17:41\n    Not After : Oct 16, 2030 00:00\n 2: Apple Root CA\n    <cert(0x1034a88d0) s: Apple Root CA i: Apple Root CA>\n    Not Before: Apr 25, 2006 21:40\n    Not After : Feb 9, 2035 21:40\n\n---\nTrust evaluation results\n{\n    RevocationInfo =     (\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n        }\n    );\n    TrustEvaluationDate = \"2026-09-22 17:37:55 +0000\";\n    TrustEvaluationID = \"E672D16A-43B4-4210-AFA4-5B8A48AB4A5E\";\n    TrustResultDetails =     (\n                {\n        },\n                {\n        },\n                {\n        }\n    );\n    TrustResultValue = 4;\n}",
        "returncode": 0,
        "status": "SUCCESS"
      },
      "certificates": [
        {
          "dateValidity": "VALID",
          "index": 0,
          "issuer": "CN=Apple Code Signing Certification Authority, OU=Certification Authority, O=Apple Inc., C=US",
          "notAfter": "Apr 27 19:29:51 2027 GMT",
          "notBefore": "Mar 30 16:34:05 2026 GMT",
          "parseReturncode": 0,
          "serial": "2E17A0A889A8FE49",
          "sha256Fingerprint": "1E:E9:D4:5F:25:11:1C:92:4A:A3:AD:69:F3:FF:FE:5D:A5:AC:36:91:BB:B2:A1:A4:8D:85:FA:D1:86:3E:AD:E1",
          "subject": "CN=macOS Software Signing, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 1,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Oct 16 00:00:00 2030 GMT",
          "notBefore": "Oct 18 17:41:25 2017 GMT",
          "parseReturncode": 0,
          "serial": "038A771EDF341786",
          "sha256Fingerprint": "76:84:3E:4C:6E:3A:CB:21:61:34:A5:7B:A8:AF:F5:12:E3:94:67:2B:39:66:B9:96:DA:80:F0:09:EE:7B:46:45",
          "subject": "CN=Apple Code Signing Certification Authority, OU=Certification Authority, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 2,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Feb  9 21:40:36 2035 GMT",
          "notBefore": "Apr 25 21:40:36 2006 GMT",
          "parseReturncode": 0,
          "serial": "02",
          "sha256Fingerprint": "B0:B1:73:0E:CB:C7:FF:45:05:14:2C:49:F1:29:5E:6E:DA:6B:CA:ED:7E:2C:68:C5:BE:91:B5:A1:10:01:F0:24",
          "subject": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA"
        }
      ],
      "designatedRequirement": {
        "output": "designated => identifier \"com.apple.TextEdit\" and anchor apple\n\nExecutable=/System/Applications/TextEdit.app/Contents/MacOS/TextEdit",
        "parseable": true,
        "returncode": 0
      },
      "details": {
        "output": "Executable=/System/Applications/TextEdit.app/Contents/MacOS/TextEdit\nIdentifier=com.apple.TextEdit\nFormat=app bundle with Mach-O universal (arm64e arm64e.x1)\nCodeDirectory v=20400 size=1099 flags=0x0(none) hashes=24+7 location=embedded\nPlatform identifier=26\nVersionPlatform=1\nVersionMin=1769472\nVersionSDK=1769472\nHash type=sha256 size=32\nCandidateCDHash sha256=39e73f1d7737ec7aee654d68b11a18f5e5b9f616\nCandidateCDHashFull sha256=39e73f1d7737ec7aee654d68b11a18f5e5b9f616b2f8b5294bb74333d841f629\nHash choices=sha256\nCMSDigest=39e73f1d7737ec7aee654d68b11a18f5e5b9f616b2f8b5294bb74333d841f629\nCMSDigestType=2\nExecutable Segment base=0\nExecutable Segment limit=163840\nExecutable Segment flags=0x1\nPage size=16384\nCDHash=39e73f1d7737ec7aee654d68b11a18f5e5b9f616\nSignature size=4202\nAuthority=macOS Software Signing\nAuthority=Apple Code Signing Certification Authority\nAuthority=Apple Root CA\nSigned Time=Aug 9, 2026 at 08:13:15\nInfo.plist entries=34\nTeamIdentifier=not set\nSealed Resources version=2 rules=2 files=0\nInternal requirements count=1 size=68\nTotal signatures=1\nChosen signature=1",
        "returncode": 0
      },
      "gatekeeper": {
        "output": "/System/Applications/TextEdit.app: accepted\nsource=Apple System",
        "returncode": 0,
        "status": "ACCEPTED"
      },
      "kind": "system",
      "name": "TextEdit",
      "path": "/System/Applications/TextEdit.app",
      "present": true,
      "verifyVerbose4": {
        "output": "/System/Applications/TextEdit.app: valid on disk\n/System/Applications/TextEdit.app: satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      },
      "verifyVerbose6": {
        "output": "/System/Applications/TextEdit.app: valid on disk\n/System/Applications/TextEdit.app: satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      }
    },
    {
      "asarIntegrity": {
        "actual": "a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a",
        "algorithm": "SHA256",
        "archiveSha256": "1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483",
        "expected": "a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a",
        "status": "PASS"
      },
      "certificateChain": {
        "output": "...certificate verification successful.\n---\nCertificate chain\n 0: Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)\n    <cert(0x10549bfd0) s: Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2) i: Developer ID Certification Authority>\n    Not Before: May 12, 2026 15:40\n    Not After : May 13, 2031 15:40\n 1: Developer ID Certification Authority\n    <cert(0x10549caf0) s: Developer ID Certification Authority i: Apple Root CA>\n    Not Before: Sep 22, 2021 18:55\n    Not After : Sep 17, 2031 00:00\n 2: Apple Root CA\n    <cert(0x10549d390) s: Apple Root CA i: Apple Root CA>\n    Not Before: Apr 25, 2006 21:40\n    Not After : Feb 9, 2035 21:40\n\n---\nTrust evaluation results\n{\n    RevocationInfo =     (\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n            valid =             {\n                anchorHash = {length = 32, bytes = 0xb0b1730e cbc7ff45 05142c49 f1295e6e ... be91b5a1 1001f024 };\n                certHash = {length = 32, bytes = 0xf16cd3c5 4c7f83ce a4bf1a3e 6a0819c8 ... 715f3506 43d2df3a };\n                checkOCSP = 0;\n                complete = 1;\n                format = 1;\n                hasDateConstraints = 0;\n                hasNameConstraints = 0;\n                hasPolicyConstraints = 0;\n                isDefinitive = 1;\n                isOnList = 0;\n                isRevoked = 0;\n                issuerHash = {length = 32, bytes = 0xb0b1730e cbc7ff45 05142c49 f1295e6e ... be91b5a1 1001f024 };\n                knownOnly = 0;\n                noCACheck = 0;\n                overridable = 0;\n                requireCT = 0;\n                valid = 0;\n            };\n        },\n                {\n            ocsp =             {\n            };\n        }\n    );\n    TrustEvaluationDate = \"2026-09-22 17:38:00 +0000\";\n    TrustEvaluationID = \"37D9BDC8-6CE6-4DC8-9FD0-8709EB5CC512\";\n    TrustResultDetails =     (\n                {\n        },\n                {\n        },\n                {\n        }\n    );\n    TrustResultValue = 4;\n}",
        "returncode": 0,
        "status": "SUCCESS"
      },
      "certificates": [
        {
          "dateValidity": "VALID",
          "index": 0,
          "issuer": "CN=Developer ID Certification Authority, OU=G2, O=Apple Inc., C=US",
          "notAfter": "May 13 15:40:26 2031 GMT",
          "notBefore": "May 12 15:40:27 2026 GMT",
          "parseReturncode": 0,
          "serial": "315B87E03811A48BD81789E1F0C20E4C",
          "sha256Fingerprint": "04:F7:47:C4:0A:6E:9B:87:39:FE:59:DA:61:CC:41:D9:51:95:44:65:9A:10:09:C5:F5:62:95:77:ED:57:ED:D5",
          "subject": "UID=2DC432GLL2, CN=Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2), OU=2DC432GLL2, O=OpenAI OpCo, LLC, C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 1,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Sep 17 00:00:00 2031 GMT",
          "notBefore": "Sep 22 18:55:10 2021 GMT",
          "parseReturncode": 0,
          "serial": "7FB4003FCD97497ACB834D92A48A7873C2845D43",
          "sha256Fingerprint": "F1:6C:D3:C5:4C:7F:83:CE:A4:BF:1A:3E:6A:08:19:C8:AA:A8:E4:A1:52:8F:D1:44:71:5F:35:06:43:D2:DF:3A",
          "subject": "CN=Developer ID Certification Authority, OU=G2, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 2,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Feb  9 21:40:36 2035 GMT",
          "notBefore": "Apr 25 21:40:36 2006 GMT",
          "parseReturncode": 0,
          "serial": "02",
          "sha256Fingerprint": "B0:B1:73:0E:CB:C7:FF:45:05:14:2C:49:F1:29:5E:6E:DA:6B:CA:ED:7E:2C:68:C5:BE:91:B5:A1:10:01:F0:24",
          "subject": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA"
        }
      ],
      "designatedRequirement": {
        "output": "designated => identifier \"com.openai.codex\" and anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and certificate leaf[subject.OU] = \"2DC432GLL2\"\n\nExecutable=/Applications/ChatGPT.app/Contents/MacOS/ChatGPT",
        "parseable": true,
        "returncode": 0
      },
      "details": {
        "output": "Executable=/Applications/ChatGPT.app/Contents/MacOS/ChatGPT\nIdentifier=com.openai.codex\nFormat=app bundle with Mach-O thin (arm64)\nCodeDirectory v=20500 size=764 flags=0x10000(runtime) hashes=13+7 location=embedded\nVersionPlatform=1\nVersionMin=851968\nVersionSDK=1703936\nHash type=sha256 size=32\nCandidateCDHash sha256=d3a816e5640ec018494cccfd2abd3badaff544c0\nCandidateCDHashFull sha256=d3a816e5640ec018494cccfd2abd3badaff544c00bdf87ddfd58eaf65ba32939\nHash choices=sha256\nCMSDigest=d3a816e5640ec018494cccfd2abd3badaff544c00bdf87ddfd58eaf65ba32939\nCMSDigestType=2\nExecutable Segment base=0\nExecutable Segment limit=16384\nExecutable Segment flags=0x1\nPage size=4096\nCDHash=d3a816e5640ec018494cccfd2abd3badaff544c0\nSignature size=9046\nAuthority=Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)\nAuthority=Developer ID Certification Authority\nAuthority=Apple Root CA\nTimestamp=Sep 18, 2026 at 12:05:34\nNotarization Ticket=stapled\nInfo.plist entries=64\nTeamIdentifier=2DC432GLL2\nRuntime Version=26.0.0\nSealed Resources version=2 rules=13 files=3823\nInternal requirements count=1 size=176\nTotal signatures=1\nChosen signature=1",
        "returncode": 0
      },
      "gatekeeper": {
        "output": "/Applications/ChatGPT.app: accepted\nsource=Notarized Developer ID",
        "returncode": 0,
        "status": "ACCEPTED"
      },
      "identity": {
        "build": "9922",
        "bundleIdentifier": "com.openai.codex",
        "version": "26.915.31945"
      },
      "kind": "installed-chatgpt",
      "name": "Installed ChatGPT",
      "path": "/Applications/ChatGPT.app",
      "present": true,
      "verifyVerbose4": {
        "output": "--prepared:/Applications/ChatGPT.app/Contents/PlugIns/CodexDockTilePlugin.docktileplugin\n--validated:/Applications/ChatGPT.app/Contents/PlugIns/CodexDockTilePlugin.docktileplugin\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Updater.app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Autoupdate\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Autoupdate\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Downloader.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Updater.app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Downloader.xpc\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Installer.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Installer.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/app_mode_loader\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/app_mode_loader\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--prepared:/Applications/Cha",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      },
      "verifyVerbose6": {
        "output": "--prepared:/Applications/ChatGPT.app/Contents/PlugIns/CodexDockTilePlugin.docktileplugin\n--validated:/Applications/ChatGPT.app/Contents/PlugIns/CodexDockTilePlugin.docktileplugin\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Updater.app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Autoupdate\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Autoupdate\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/Updater.app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Installer.xpc\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Downloader.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Installer.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/XPCServices/Downloader.xpc\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Sparkle.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/.\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/app_mode_loader\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/app_mode_loader\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--validated:/Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--prepared:/Applications/Cha",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      }
    },
    {
      "asarIntegrity": {
        "actual": "a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a",
        "algorithm": "SHA256",
        "archiveSha256": "1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483",
        "expected": "a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a",
        "status": "PASS"
      },
      "certificateChain": {
        "output": "...certificate verification successful.\n---\nCertificate chain\n 0: Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)\n    <cert(0x1017e0ad0) s: Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2) i: Developer ID Certification Authority>\n    Not Before: May 12, 2026 15:40\n    Not After : May 13, 2031 15:40\n 1: Developer ID Certification Authority\n    <cert(0x1017e14d0) s: Developer ID Certification Authority i: Apple Root CA>\n    Not Before: Sep 22, 2021 18:55\n    Not After : Sep 17, 2031 00:00\n 2: Apple Root CA\n    <cert(0x1017e1bd0) s: Apple Root CA i: Apple Root CA>\n    Not Before: Apr 25, 2006 21:40\n    Not After : Feb 9, 2035 21:40\n\n---\nTrust evaluation results\n{\n    RevocationInfo =     (\n                {\n            ocsp =             {\n            };\n        },\n                {\n            ocsp =             {\n            };\n            valid =             {\n                anchorHash = {length = 32, bytes = 0xb0b1730e cbc7ff45 05142c49 f1295e6e ... be91b5a1 1001f024 };\n                certHash = {length = 32, bytes = 0xf16cd3c5 4c7f83ce a4bf1a3e 6a0819c8 ... 715f3506 43d2df3a };\n                checkOCSP = 0;\n                complete = 1;\n                format = 1;\n                hasDateConstraints = 0;\n                hasNameConstraints = 0;\n                hasPolicyConstraints = 0;\n                isDefinitive = 1;\n                isOnList = 0;\n                isRevoked = 0;\n                issuerHash = {length = 32, bytes = 0xb0b1730e cbc7ff45 05142c49 f1295e6e ... be91b5a1 1001f024 };\n                knownOnly = 0;\n                noCACheck = 0;\n                overridable = 0;\n                requireCT = 0;\n                valid = 0;\n            };\n        },\n                {\n            ocsp =             {\n            };\n        }\n    );\n    TrustEvaluationDate = \"2026-09-22 17:38:13 +0000\";\n    TrustEvaluationID = \"8EADCF3D-F832-4F6B-B19B-9ED32E8A55F3\";\n    TrustResultDetails =     (\n                {\n        },\n                {\n        },\n                {\n        }\n    );\n    TrustResultValue = 4;\n}",
        "returncode": 0,
        "status": "SUCCESS"
      },
      "certificates": [
        {
          "dateValidity": "VALID",
          "index": 0,
          "issuer": "CN=Developer ID Certification Authority, OU=G2, O=Apple Inc., C=US",
          "notAfter": "May 13 15:40:26 2031 GMT",
          "notBefore": "May 12 15:40:27 2026 GMT",
          "parseReturncode": 0,
          "serial": "315B87E03811A48BD81789E1F0C20E4C",
          "sha256Fingerprint": "04:F7:47:C4:0A:6E:9B:87:39:FE:59:DA:61:CC:41:D9:51:95:44:65:9A:10:09:C5:F5:62:95:77:ED:57:ED:D5",
          "subject": "UID=2DC432GLL2, CN=Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2), OU=2DC432GLL2, O=OpenAI OpCo, LLC, C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 1,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Sep 17 00:00:00 2031 GMT",
          "notBefore": "Sep 22 18:55:10 2021 GMT",
          "parseReturncode": 0,
          "serial": "7FB4003FCD97497ACB834D92A48A7873C2845D43",
          "sha256Fingerprint": "F1:6C:D3:C5:4C:7F:83:CE:A4:BF:1A:3E:6A:08:19:C8:AA:A8:E4:A1:52:8F:D1:44:71:5F:35:06:43:D2:DF:3A",
          "subject": "CN=Developer ID Certification Authority, OU=G2, O=Apple Inc., C=US"
        },
        {
          "dateValidity": "VALID",
          "index": 2,
          "issuer": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA",
          "notAfter": "Feb  9 21:40:36 2035 GMT",
          "notBefore": "Apr 25 21:40:36 2006 GMT",
          "parseReturncode": 0,
          "serial": "02",
          "sha256Fingerprint": "B0:B1:73:0E:CB:C7:FF:45:05:14:2C:49:F1:29:5E:6E:DA:6B:CA:ED:7E:2C:68:C5:BE:91:B5:A1:10:01:F0:24",
          "subject": "C=US, O=Apple Inc., OU=Apple Certification Authority, CN=Apple Root CA"
        }
      ],
      "designatedRequirement": {
        "output": "designated => identifier \"com.openai.codex\" and anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and certificate leaf[subject.OU] = \"2DC432GLL2\"\n\nExecutable=<TEMP>",
        "parseable": true,
        "returncode": 0
      },
      "details": {
        "output": "Executable=<TEMP>\nIdentifier=com.openai.codex\nFormat=app bundle with Mach-O thin (arm64)\nCodeDirectory v=20500 size=764 flags=0x10000(runtime) hashes=13+7 location=embedded\nVersionPlatform=1\nVersionMin=851968\nVersionSDK=1703936\nHash type=sha256 size=32\nCandidateCDHash sha256=d3a816e5640ec018494cccfd2abd3badaff544c0\nCandidateCDHashFull sha256=d3a816e5640ec018494cccfd2abd3badaff544c00bdf87ddfd58eaf65ba32939\nHash choices=sha256\nCMSDigest=d3a816e5640ec018494cccfd2abd3badaff544c00bdf87ddfd58eaf65ba32939\nCMSDigestType=2\nExecutable Segment base=0\nExecutable Segment limit=16384\nExecutable Segment flags=0x1\nPage size=4096\nCDHash=d3a816e5640ec018494cccfd2abd3badaff544c0\nSignature size=9046\nAuthority=Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)\nAuthority=Developer ID Certification Authority\nAuthority=Apple Root CA\nTimestamp=Sep 18, 2026 at 12:05:34\nNotarization Ticket=stapled\nInfo.plist entries=64\nTeamIdentifier=2DC432GLL2\nRuntime Version=26.0.0\nSealed Resources version=2 rules=13 files=3823\nInternal requirements count=1 size=176\nTotal signatures=1\nChosen signature=1",
        "returncode": 0
      },
      "gatekeeper": {
        "output": "<TEMP> accepted\nsource=Notarized Developer ID",
        "returncode": 0,
        "status": "ACCEPTED"
      },
      "identity": {
        "build": "9922",
        "bundleIdentifier": "com.openai.codex",
        "version": "26.915.31945"
      },
      "kind": "official-chatgpt",
      "name": "Official clean ChatGPT",
      "path": "<TEMP>",
      "present": true,
      "verifyVerbose4": {
        "output": "--prepared:<TEMP> Framework.framework/Versions/Current/.\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/app_mode_loader\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/app_mode_loader\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/browser_crashpad_handler\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/browser_crashpad_handler\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:<TEMP> Framework.framework/Versions/Current/.\n--prepared:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n<TEMP> valid on disk\n<TEMP> satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      },
      "verifyVerbose6": {
        "output": "--prepared:<TEMP> Framework.framework/Versions/Current/.\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/app_mode_loader\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/app_mode_loader\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/browser_crashpad_handler\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/browser_crashpad_handler\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Alerts).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Alerts).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif GPU).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif Renderer).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Aperitif).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (GPU).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Renderer).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/Codex (Service).app\n--prepared:<TEMP> Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:<TEMP> Framework.framework/Versions/Current/Helpers/web_app_shortcut_copier\n--validated:<TEMP> Framework.framework/Versions/Current/.\n--prepared:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n--validated:<TEMP>\n--prepared:<TEMP>\n--validated:<TEMP>\n<TEMP> valid on disk\n<TEMP> satisfies its Designated Requirement",
        "returncode": 0,
        "structural": "STRUCTURAL_SIGNATURE_INTACT",
        "structuralMarkers": [],
        "trust": "TRUST_EVALUATION_PASS",
        "trustMarkers": []
      }
    }
  ],
  "decision": {
    "classification": "TRUST_ENVIRONMENT_HEALTHY",
    "degradedGateSafeToConsider": false,
    "phase8Decision": "STRICT_TRUST_GATE_USABLE",
    "strictTrustGateUsable": true
  },
  "keychains": {
    "output": "\"<HOME>/Library/Keychains/login.keychain-db\"\n    \"/Library/Keychains/System.keychain\"",
    "returncode": 0
  },
  "logs": {
    "findings": [
      "Timestamp               Ty Process[PID:TID]"
    ],
    "returncode": 0,
    "status": "READABLE"
  },
  "roots": {
    "Apple Root CA": {
      "present": true,
      "returncode": 0
    },
    "Apple Root CA - G2": {
      "present": true,
      "returncode": 0
    },
    "Apple Root CA - G3": {
      "present": true,
      "returncode": 0
    },
    "Apple Worldwide Developer Relations Certification Authority": {
      "present": true,
      "returncode": 0
    },
    "Developer ID Certification Authority": {
      "present": true,
      "returncode": 0
    }
  },
  "services": {
    "processCheck": {
      "returncode": 0,
      "securityd": true,
      "trustd": true
    },
    "securityd": {
      "output": "system/com.apple.securityd = {\n\tactive count = 2\n\tpath = /System/Library/LaunchDaemons/com.apple.securityd.plist\n\ttype = LaunchDaemon\n\tstate = running\n\n\tprogram = /usr/sbin/securityd\n\targuments = {\n\t\t/usr/sbin/securityd\n\t\t-i\n\t}\n\n\tdefault environment = {\n\t\tPATH => /usr/bin:/bin:/usr/sbin:/sbin\n\t}\n\n\tenvironment = {\n\t\tOSLogRateLimit => 64\n\t\tMallocSpaceEfficient => 1\n\t\tSECURITY_CSP_PAGE_ISOLATE_ALLOCATIONS => 1\n\t\t__CF_USER_TEXT_ENCODING => 0x0:0:0\n\t\t__CFPREFERENCES_AVOID_DAEMON => 1\n\t\tXPC_SERVICE_NAME => com.apple.securityd\n\t}\n\n\tdomain = system\n\tminimum runtime = 10\n\tbase minimum runtime = 10\n\texit timeout = 5\n\truns = 1\n\tpid = 618\n\timmediate reason = speculative\n\tforks = 0\n\texecs = 1\n\tinitialized = 1\n\ttrampolined = 1\n\tstarted suspended = 0\n\tproxy started suspended = 0\n\tchecked allocations = 0 (queried = 1)\n\tchecked allocations reason = no host\n\tchecked allocations flags = 0x0\n\tlast exit code = (never exited)\n\n\tendpoints = {\n\t\t\"com.apple.SecurityServer\" = {\n\t\t\tport = 0x9303\n\t\t\tactive = 1\n\t\t",
      "returncode": 0,
      "status": "RUNNING"
    },
    "trustdGui": {
      "output": "Bad request.\nCould not find service \"com.apple.trustd\" in domain for user gui: 502",
      "returncode": 113,
      "status": "UNAVAILABLE_OR_NOT_RUNNING"
    },
    "trustdSystem": {
      "output": "system/com.apple.trustd = {\n\tactive count = 2\n\tpath = /System/Library/LaunchDaemons/com.apple.trustd.plist\n\ttype = LaunchDaemon\n\tstate = running\n\n\tprogram = /usr/libexec/trustd\n\targuments = {\n\t\t/usr/libexec/trustd\n\t}\n\n\tdefault environment = {\n\t\tPATH => /usr/bin:/bin:/usr/sbin:/sbin\n\t}\n\n\tenvironment = {\n\t\tOSLogRateLimit => 64\n\t\tMallocSpaceEfficient => 1\n\t\tWAIT4DEBUGGER => NO\n\t\tDEBUGSCOPE => -policy-node,policy-set,policy,alloc,trust,bind,profile,trace,dbconn,OTR,serverxpc,sqlite3,error_thee_well\n\t\tXPC_SERVICE_NAME => com.apple.trustd\n\t}\n\n\tdomain = system\n\tusername = _trustd\n\n\tumask = 33\n\tminimum runtime = 10\n\tbase minimum runtime = 10\n\texit timeout = 5\n\truns = 2\n\tpid = 14952\n\timmediate reason = ipc (mach)\n\tforks = 0\n\texecs = 1\n\tinitialized = 1\n\ttrampolined = 1\n\tstarted suspended = 0\n\tproxy started suspended = 0\n\tchecked allocations = 0 (queried = 1)\n\tchecked allocations reason = no host\n\tchecked allocations flags = 0x0\n\tlast exit code = 0\n\n\tendpoints = {\n\t\t\"com.apple.trustd\" = {\n\t\t\tport",
      "returncode": 0,
      "status": "RUNNING"
    }
  },
  "system": {
    "architecture": {
      "output": "arm64",
      "returncode": 0
    },
    "clockPlausible": true,
    "currentTime": "2026-09-23T01:37:51.709304+08:00",
    "swVers": {
      "output": "ProductName:\t\tmacOS\nProductVersion:\t\t27.0\nBuildVersion:\t\t26A428",
      "returncode": 0
    },
    "uname": {
      "output": "Darwin <HOST> 27.0.0 Darwin Kernel Version 27.0.0: Tue Aug 11 21:05:27 PDT 2026; root:xnu-13432.1.9~1/RELEASE_ARM64_T8103 arm64",
      "returncode": 0
    },
    "utcOffset": "+0800"
  },
  "trustSettings": {
    "admin": {
      "explicitDeny": false,
      "output": "Number of trusted certs = 1\nCert 0: MicrodoneCA\n   Number of trust settings : 0",
      "returncode": 0,
      "status": "READABLE"
    },
    "system": {
      "explicitDeny": false,
      "output": "Number of trusted certs = 157\nCert 0: DigiCert TLS ECC P384 Root G5\n   Number of trust settings : 0\nCert 1: XRamp Global Certification Authority\n   Number of trust settings : 0\nCert 2: OISTE WISeKey Global Root GB CA\n   Number of trust settings : 0\nCert 3: Amazon Root CA 2\n   Number of trust settings : 0\nCert 4: Actalis Authentication Root CA\n   Number of trust settings : 0\nCert 5: ISRG Root X1\n   Number of trust settings : 0\nCert 6: Apple Platform Code Signing ECC Root CA - G1\n   Number of trust settings : 0\nCert 7: ACCVRAIZ1\n   Number of trust settings : 0\nCert 8: Certainly Root R1\n   Number of trust settings : 0\nCert 9: Certum Trusted Root CA\n   Number of trust settings : 0\nCert 10: TUBITAK Kamu SM SSL Kok Sertifikasi - Surum 1\n   Number of trust settings : 0\nCert 11: GTS Root R3\n   Number of trust settings : 0\nCert 12: Certum Trusted Network CA\n   Number of trust settings : 0\nCert 13: Certainly Root E1\n   Number of trust settings : 0\nCert 14: certSIGN ROOT CA\n   Number of trust settings : 0\nCert 15: SwissSign Gold CA - G2\n   Number of trust settings : 0\nCert 16: T-TeleSec GlobalRoot Class 2\n   Number of trust settings : 0\nCert 17: Entrust.net Certification Authority (2048)\n   Number of trust settings : 0\nCert 18: D-TRUST Root Class 3 CA 2 2009\n   Number of trust settings : 0\nCert 19: DigiCert Assured ID Root G2\n   Number of trust settings : 0\nCert 20: ePKI Root Certification Authority\n   Number of trust settings : 0\nCert 21: GeoTrust Primary Certification Authority - G2\n   Number of trust settings : 0\nCert 22: GlobalSign\n   Number of trust settings : 0\nCert 23: USERTrust RSA Certification Authority\n   Number of trust settings : 0\nCert 24: Atos TrustedRoot Root CA ECC TLS 2021\n   Number of trust settings : 0\nCert 25: Sectigo Public Email Protection Root R46\n   Number of trust settings : 0\nCert 26: TeliaSonera Root CA v1\n   Number of trust settings : 0\nCert 27: Starfield Class 2 Certification Authority\n   Number of trust settings : 0\nCert 28: AffirmTrust Premium E",
      "returncode": 0,
      "status": "READABLE"
    },
    "user": {
      "explicitDeny": false,
      "output": "Number of trusted certs = 1\nCert 0: www.ygdy8.net\n   Number of trust settings : 2\n   Trust Setting 0:\n      Policy OID            : SSL\n      Policy String         : www.ygdy8.net\n      Allowed Error         : CSSMERR_TP_CERT_EXPIRED\n      Result Type           : kSecTrustSettingsResultTrustAsRoot\n   Trust Setting 1:\n      Policy OID            : SSL\n      Policy String         : www.ygdy8.net\n      Allowed Error         : Host name mismatch\n      Result Type           : kSecTrustSettingsResultTrustAsRoot",
      "returncode": 0,
      "status": "READABLE"
    }
  }
}
```
