# tilt-extension-suse-rda

A [Tilt](https://tilt.dev) extension for SUSE [Rancher Developer Access](https://www.suse.com/products/rancher/developer-access/).

Wraps Cloud Native Buildpacks (via `pack`), Helm install, and service
port-forwarding into a single declarative call (`suse_app(...)`). Designed
for projects scaffolded by [`rda new`](https://github.com/idefxH/rda-cli)
from a SUSE RDA opinion bundle, but usable from any Tiltfile that wants
the same conventions.

## What it gives you

```python
load_dynamic('https://raw.githubusercontent.com/idefxH/tilt-extension-suse-rda/main/Tiltfile')

suse_app(
    name='payment-service',
    language='nodejs',
    port=8080,
    services={'database': 'postgresql'},
)
```

That replaces ~30 lines of `docker_build` / `helm` / `k8s_resource` boilerplate
with one call.

Effects:
- Builds `payment-service:dev` via `pack build` using the Paketo Node.js
  buildpack on the `paketobuildpacks/builder-jammy-base` builder.
- Configures live-update: edits to `./src/**` sync into the running container;
  changes to `package.json` re-run `npm install`.
- Renders the Helm chart at `.` with `values.yaml` and applies it.
- Port-forwards `localhost:8080` to the app and `localhost:5432` to the
  Postgres sidecar (the conventional port for `postgresql`).
- Organises Tilt's UI: app under "app", services under "services".

## Prerequisites

- Tilt 0.33+
- `pack` CLI in `$PATH` (https://buildpacks.io)
- `helm` CLI in `$PATH`
- A running Kubernetes cluster (Rancher Desktop, k3d, kind, etc.)
- Network access to Docker Hub for the Paketo builder (the first build
  pulls `paketobuildpacks/builder-jammy-base:latest`)

## Supported languages

| `language` | Default buildpack | Live update |
|---|---|---|
| `nodejs` | `paketo-buildpacks/nodejs` | Sync `./src`, re-run `npm install` on `package.json` change |
| `python` | `paketo-buildpacks/python` | Sync `./src`, re-run `pip install` on requirement-file changes |
| `java` | `paketo-buildpacks/java` | Full rebuild on any change (Spring DevTools support is on the roadmap) |
| `go` | `paketo-buildpacks/go` | Full rebuild on any change |

## Conventional service ports

For services declared in `services={...}`, the extension forwards the
canonical local port:

| Service type | Local port |
|---|---|
| `postgresql` | 5432 |
| `redis` | 6379 |
| `mysql` | 3306 |
| `mongodb` | 27017 |
| `kafka` | 9092 |
| `rabbitmq` | 5672 |
| `nats` | 4222 |

A type not in this list still gets a Tilt UI workload entry, just no port-forward.
Add a follow-up `k8s_resource(workload='<name>-<binding>', port_forwards='...')`
if you need a custom mapping.

## SUSE-AppCo buildpacks (future)

Today the extension uses Paketo builders (Ubuntu Jammy-based). When the
SUSE-AppCo buildpacks land, switch with:

```python
suse_app(
    ...,
    builder_image='registry.suse.com/rda/builder:latest',
)
```

The builder is the only thing that changes — the buildpack composition and
live-update patterns stay the same. SUSE-AppCo buildpacks target SLE BCI
images and align with the supply chain story documented in the rda spec.

## Function signature

```python
suse_app(
    name,                       # required, str
    language,                   # required, 'nodejs' | 'python' | 'java' | 'go'
    port=8080,
    services={},                # dict of binding-name -> service-type
    chart_path='.',
    chart_values_files=['values.yaml'],
    builder_image=None,         # default: Paketo full builder
    extra_buildpacks=[],        # additional CNB buildpacks
    additional_env={},          # pack build --env entries
    live_update_paths=None,     # override per-language defaults
    ui_labels=None,             # override workload labels in Tilt UI
)
```

See [`Tiltfile`](./Tiltfile) for the full docstring and inline comments.

## Examples

[`examples/nodejs-hello/`](./examples/nodejs-hello/) — a minimal Node.js
app using suse_app() against a single-file Helm chart.

## Development

This extension is plain Starlark. To test changes:

```bash
cd examples/nodejs-hello
tilt up --port 10350
# edit ../../Tiltfile, hit r in Tilt to reload
```

## Status

v0.1.0. Intentionally hand-written for fast iteration; will be regenerated
from a PCD spec once Starlark gets a deployment template upstream
(see [PCD project](https://github.com/mge1512/pcd)).

## License

Apache-2.0
