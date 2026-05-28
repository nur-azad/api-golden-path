# LEGO API Golden Path — Case Study Demo

A working prototype for the **API Developer Portal** proposal: a single, opinionated path for product squads to validate, register, and discover APIs — without the platform team becoming a bottleneck.

Built for the LEGO Group Senior Software Engineer (API Developer Portal) — 3rd Round case study.

---

## What this demonstrates


| Capability                                                 | Artefact                                     |
| ---------------------------------------------------------- | -------------------------------------------- |
| Local spec validation (10 rules, error + warning severity) | `platform-tooling/python/apictl.py validate` |
| Backstage catalog metadata generation                      | `apictl.py validate --emit-backstage`        |
| Dry-run catalog registration                               | `apictl.py register`                         |
| Custom Spectral ruleset (3 org rules)                      | `platform-tooling/.spectral.yaml`            |
| CI gate — bad spec blocked, good spec passes              | `.github/workflows/validate.yaml`            |
| Legacy API spec extraction from traffic capture            | `platform-tooling/python/extract.py`         |
| API readiness scorecard (interactive HTML)                  | `api-readiness.html`                         |
| Adoption dashboard                                         | `dashboard.html`                             |
| Case study presentation (21 slides)                        | `presentation.html`                          |

---

## Full demo sequence

All steps use a single Docker image — no local Python or .NET runtime required.

**bash**
```bash
# One-time build (run from repo root)
docker build -t green-path-validator platform-tooling/python
docker build -t green-path-spectral platform-tooling
```

**PowerShell**
```powershell
# One-time build (run from repo root)
docker build -t green-path-validator platform-tooling/python
docker build -t green-path-spectral platform-tooling
```

---

**bash**
```bash
# 1. Show failure mode — bad spec blocked at gate
docker run --rm \
  -v "${PWD}/sample-product-api:/workspace" \
  green-path-validator validate /workspace/bad_openapi.yaml
# → 2 errors found, 5 warnings found. Exit code 1.

# 2. Show golden path — compliant spec passes, emits Backstage YAML
docker run --rm \
  -v "${PWD}/sample-product-api:/workspace" \
  green-path-validator validate /workspace/sample_openapi.yaml --emit-backstage
# → No issues found — spec looks good.
# → Wrote Backstage metadata to /workspace/backstage-component.yaml

# 3. Lifecycle close — dry-run catalog registration
docker run --rm \
  -v "${PWD}/sample-product-api:/workspace" \
  green-path-validator register /workspace/sample_openapi.yaml
# → [DRY RUN] Would POST to: http://localhost:7007/api/catalog/locations
```

**PowerShell**
```powershell
# 1. Show failure mode — bad spec blocked at gate
docker run --rm `
  -v "${PWD}/sample-product-api:/workspace" `
  green-path-validator validate /workspace/bad_openapi.yaml
# → 2 errors found, 5 warnings found. Exit code 1.

# 2. Show golden path — compliant spec passes, emits Backstage YAML
docker run --rm `
  -v "${PWD}/sample-product-api:/workspace" `
  green-path-validator validate /workspace/sample_openapi.yaml --emit-backstage
# → No issues found — spec looks good.
# → Wrote Backstage metadata to /workspace/backstage-component.yaml

# 3. Lifecycle close — dry-run catalog registration
docker run --rm `
  -v "${PWD}/sample-product-api:/workspace" `
  green-path-validator register /workspace/sample_openapi.yaml
# → [DRY RUN] Would POST to: http://localhost:7007/api/catalog/locations
```

Then open `api-readiness.html` in a browser — click any check row to expand detail and watch the progress bar animate.

---

**bash**
```bash
# 4. Legacy API — extract an OpenAPI spec from captured traffic, then validate
docker run --rm \
  -v "${PWD}/platform-tooling/python:/workspace" \
  green-path-validator extract /workspace/traffic.har --output /workspace/extracted_openapi.yaml
# → Success! Generated 'extracted_openapi.yaml' with response schemas from network logs.

docker run --rm \
  -v "${PWD}/platform-tooling/python:/workspace" \
  green-path-validator validate /workspace/extracted_openapi.yaml
# → 0 errors, 2 warnings (SECURITY, OPENTELEMETRY_TAG)

# 5. Spectral org-rules gate (run against compliant spec)
docker run --rm \
  -v "${PWD}/sample-product-api:/workspace" \
  -v "${PWD}/platform-tooling/.spectral.yaml:/.spectral.yaml" \
  green-path-spectral /workspace/sample_openapi.yaml --ruleset /.spectral.yaml
```

**PowerShell**
```powershell
# 4. Legacy API — extract an OpenAPI spec from captured traffic, then validate
docker run --rm `
  -v "${PWD}/platform-tooling/python:/workspace" `
  green-path-validator extract /workspace/traffic.har --output /workspace/extracted_openapi.yaml
# → Success! Generated 'extracted_openapi.yaml' with response schemas from network logs.

docker run --rm `
  -v "${PWD}/platform-tooling/python:/workspace" `
  green-path-validator validate /workspace/extracted_openapi.yaml
# → 0 errors, 2 warnings (SECURITY, OPENTELEMETRY_TAG)

# 5. Spectral org-rules gate (run against compliant spec)
docker run --rm `
  -v "${PWD}/sample-product-api:/workspace" `
  -v "${PWD}/platform-tooling/.spectral.yaml:/.spectral.yaml" `
  green-path-spectral /workspace/sample_openapi.yaml --ruleset /.spectral.yaml
```

`traffic.har` was captured live using mitmproxy as a proxy in front of the running .NET service. Existing har-to-OpenAPI tools did not produce usable output from mitmproxy's netlog format, so the `extract` command reads the length-prefix encoding directly. Works against any HTTP service regardless of language or framework.

---

## Repository structure

```
.github/workflows/validate.yaml      CI pipeline (bad spec fails gate, good spec emits artifact)

platform-tooling/
  python/
    apictl.py                         CLI: validate + register commands (Click + Rich)
    extract.py                        Legacy spec extraction from mitmproxy traffic capture
    traffic.har                       Captured mitmproxy session (sample .NET API)
    extracted_openapi.yaml            Generated by extract.py
    Dockerfile                        Containerised validator image
    requirements.txt
  .spectral.yaml                      Spectral ruleset — 3 custom org rules

sample-product-api/
  sample_openapi.yaml                 Compliant spec (all rules pass)
  bad_openapi.yaml                    Non-compliant spec (2 errors, 5 warnings — fails CI gate)
  backstage-component.yaml            Generated by --emit-backstage
  sample-dotnet/                      .NET 8 sample API (Swashbuckle, built in CI)

api-readiness.html                    Interactive API readiness scorecard
dashboard.html                        Adoption dashboard (Chart.js, 12-month rollout model)
presentation.html                     Case study slides (21 slides, speaker notes)
```

---

## Run locally

### Custom validator (Python)

```bash
pip install -r platform-tooling/python/requirements.txt

# Validate
python platform-tooling/python/apictl.py validate sample-product-api/sample_openapi.yaml

# Validate and emit Backstage YAML
python platform-tooling/python/apictl.py validate sample-product-api/sample_openapi.yaml --emit-backstage

# Dry-run catalog registration (requires backstage-component.yaml from step above)
python platform-tooling/python/apictl.py register sample-product-api/sample_openapi.yaml

# Treat warnings as errors (strict mode)
python platform-tooling/python/apictl.py validate sample-product-api/sample_openapi.yaml --strict
```

### Custom validator (Docker)

```bash
docker build -t green-path-python-validator platform-tooling/python

docker run --rm -v "${PWD}/sample-product-api:/workspace" \
  green-path-python-validator validate /workspace/sample_openapi.yaml --emit-backstage
```

### Spectral ruleset (Docker)

```bash
docker build -t green-path-spectral platform-tooling

docker run --rm \
  -v "${PWD}/sample-product-api:/workspace" \
  -v "${PWD}/platform-tooling/.spectral.yaml:/workspace/.spectral.yaml" \
  green-path-spectral /workspace/sample_openapi.yaml --ruleset /workspace/.spectral.yaml
```

### .NET sample

```bash
dotnet build sample-product-api/sample-dotnet/ApiDemo.csproj
```

### Legacy spec extraction

```bash
cd platform-tooling/python
python extract.py
# → extracted_openapi.yaml written

python apictl.py validate extracted_openapi.yaml
# → 0 errors, 2 warnings
```

---

## Validation rules

**apictl.py** enforces 10 rules:


| ID                      | Severity | Check                                       |
| ----------------------- | -------- | ------------------------------------------- |
| `OPENAPI_PRESENT`       | error    | OpenAPI field present, version 3.x          |
| `INFO_TITLE`            | error    | `info.title` provided                       |
| `INFO_VERSION`          | warning  | Semantic versioning (MAJOR.MINOR.PATCH)     |
| `PATHS`                 | error    | At least one endpoint declared              |
| `RESPONSES_HAVE_SCHEMA` | error    | Each response declares`content` with schema |
| `SECURITY`              | warning  | `components.securitySchemes` declared       |
| `OPENTELEMETRY_TAG`     | warning  | `x-opentelemetry` metadata present          |
| `PARAM_DESCRIPTIONS`    | warning  | All parameters include a description        |
| `UNIQUE_OPERATION_IDS`  | warning  | No duplicate`operationId` values            |
| `PATH_PREFIX`           | warning  | Paths use`/api` or `/v` prefix              |

**Spectral** adds 3 org-specific rules: `api-contact-required`, `api-path-versioning`, `api-health-check-convention`.

---

## CI workflow

The GitHub Actions workflow (`.github/workflows/validate.yaml`) runs **two parallel jobs**:

**`validate-bad-spec` — fails the gate (expected)**

- Runs `apictl.py validate bad_openapi.yaml` → 2 errors, exit code 1, job fails red
- Runs Spectral against the bad spec → surfaces additional violations

**`validate-good-spec` — golden path (must pass)**

- Builds the .NET sample (`dotnet build`)
- Runs `apictl.py validate sample_openapi.yaml --emit-backstage` — hard gate
- Runs Spectral against the good spec — hard gate on severity `error`
- Uploads `backstage-component.yaml` as a workflow artifact

The side-by-side red/green result is the CI demo: one job shows what a bad contract looks like caught at the gate, the other shows the full golden path running clean.
