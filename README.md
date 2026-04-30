# tilt-extension-suse-rda

Tilt extension for SUSE Rancher Developer Access.

Wraps Cloud Native Buildpacks (via `pack`), Helm install, and service
port-forwarding into a single declarative call (`suse_app(...)`).

## Use

```python
v1alpha1.extension_repo(
    name='suse-rda',
    url='https://github.com/idefxH/tilt-extension-suse-rda',
)
v1alpha1.extension(
    name='suse-rda',
    repo_name='suse-rda',
    repo_path='suse_rda',
)
load('ext://suse-rda', 'suse_app')

suse_app(
    name='my-app',
    language='nodejs',
    port=8080,
)
```

That replaces ~30 lines of `docker_build` / `helm` / `k8s_resource` boilerplate
with one call. **Service port-forwards are auto-discovered from `chart/values.yaml`** — every entry under `suse-library.services[]` with `provisioning: local` AND a matching `<chart>.enabled: true` gets a port-forward registered. The Tiltfile stays in lockstep with `values.yaml` automatically; you don't list services in two places.

Entries with `provisioning: shared` or `provisioning: external` are skipped (no in-cluster workload to forward). Entries whose sub-chart is not enabled are also skipped (no workload deployed).

The pre-DSL legacy auto-discovery (`<chart>.enabled` without `services[]`) was dropped in v0.2.0 alongside bundle v0.10+. If you're on a bundle ≤ v0.9, either upgrade the bundle or pin the extension to its 0.1.x line.

Pass `services={'<binding>': '<type>'}` only when you want to register a service the chart doesn't deploy itself, or narrow the auto-discovered set to a subset. Tilt fetches and caches the extension repo automatically; restart Tilt to pick up updates.

## Prerequisites

- Tilt 0.33+
- `pack` CLI in `$PATH` (https://buildpacks.io)
- `helm` CLI in `$PATH`
- A running Kubernetes cluster (Rancher Desktop, k3d, kind, etc.)

## Repository layout

```
tilt-extension-suse-rda/
├── README.md
├── LICENSE
├── suse_rda/
│   └── Tiltfile          # the extension itself (loaded as ext://suse-rda)
└── examples/
    └── nodejs-hello/     # minimal smoke-test consuming the extension
```

The `suse_rda/` directory name follows the Tilt convention where each
extension in a repo lives in a subdirectory named after itself.

## Supported languages

| `language` | Default buildpack | Live update |
|---|---|---|
| `nodejs` | `paketo-buildpacks/nodejs` | Sync `./src`, re-run `npm install` on `package.json` change |
| `python` | `paketo-buildpacks/python` | Sync `./src`, re-run `pip install` on requirement-file changes |
| `java` | `paketo-buildpacks/java` | Full rebuild on any change |
| `go` | `paketo-buildpacks/go` | Full rebuild on any change |

## Conventional service ports

For each service auto-discovered from `chart/values.yaml` (or passed
explicitly via `services={...}`), the extension forwards the canonical
local port:

| Service type | Local port |
|---|---|
| `postgresql` | 5432 |
| `redis` | 6379 |
| `mysql` | 3306 |
| `mongodb` | 27017 |
| `kafka` | 9092 |
| `rabbitmq` | 5672 |
| `nats` | 4222 |

## SUSE-AppCo buildpacks (future)

When the SUSE-AppCo buildpacks land, override the builder:

```python
suse_app(..., builder_image='registry.suse.com/rda/builder:latest')
```

## Where image-level gates fit (forward-looking)

`suse_app(...)` is the right hook for **image-level gates** — checks
that run at `pack build` time, before Tilt deploys anything to the
cluster. These are Layer 1 of RDA's four-layer defense model. The
canonical reference is [`rda-docs/concepts/gates.md`](https://github.com/idefxH/rda-docs/blob/main/concepts/gates.md);
the anchor in the rda CLI spec is the `BEHAVIOR: promote` NOTES in
[`rda-cli/rda.md`](https://github.com/idefxH/rda-cli/blob/main/rda.md)
under "Layered-defense model".

The four layers, scoped to what each can see:

| Layer | When | Scope | Owner |
|---|---|---|---|
| 1. image-time | `pack build` | the app image | this extension (`suse_app`) + buildpack stack |
| 2. template-time | every `helm template` | rendered DSL | `rda-opinion-bundle-example` library helpers |
| 3. promote-time | `rda promote` | declared chart deps + rendered manifests | `rda` CLI |
| 4. admission-time | cluster admission | live applies | cluster operator's Kubewarden policies |

Each layer catches what only it can see; later layers exist as
defense in depth, not as substitutes. A buildpack-time CVE check
cannot see `services[].type=mongodb`; a promote-time
`forbidden_charts` gate cannot see an unsigned base image.

### Planned Layer 1 gates

Scoped to the app image only:

- **CVE scan** — fail the build if grype/trivy finds critical or
  high CVEs in the app's deps or base layer. Severity threshold
  configurable via the corp overlay.
- **Image signature** — verify (or produce) a cosign signature
  against the corp KMS key. Pairs with Layer 3's `cosign_verify`
  for AppCo sub-chart images.
- **SBOM emission** — paketo already produces SBOMs; the extension
  surfaces them as a Tilt artefact and stages them for the
  promotion record.
- **License scan** — fail on copyleft licenses if the corp overlay
  forbids them.

### Status

Spec-only today: `suse_app(...)` does not yet take gate-related
flags. Tracking issue: idefxH/tilt-extension-suse-rda#1 (to be
filed). The promote-time and template-time layers are already
shipping; this layer comes online when the SUSE-AppCo buildpacks
do, since the corp-curated image gates need a corp-curated builder
to run inside.

## License

Apache-2.0
