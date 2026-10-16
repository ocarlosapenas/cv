# schemas

| File | What | Source |
|---|---|---|
| `cv.schema.json` | Schema of `cv.yaml` (this repository) | Written here |
| `jsonresume-1.3.1.schema.json` | JSON Resume schema used to validate `build/<variant>/resume.json` | Vendored, unchanged, from `@jsonresume/schema` 1.3.1 (MIT, © 2024 JSON Resume) |

Provenance of the vendored JSON Resume schema:

- npm package `@jsonresume/schema@1.3.1`, published 2026-07-22.
- Tarball integrity (npm `dist.integrity`), verified on download:
  `sha512-S9zH1vmS67b1Ld6p9A+sHiZgqZox4lWTVHtca3VarRVkRtp3C/EMQ2bSNlO39+o+0OZbrY+Srnn7Q8uJOtxZhQ==`.
- `package/schema.json` SHA256: `a07eedd3d86ac5bb61d72e136d788269e35baf42c35391e15d0be39b3dc5a4bd`.

It is vendored instead of installed so validation needs neither npm nor network.
