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
    name='payment-service',
    language='nodejs',
    port=8080,
    services={'database': 'postgresql'},
)
```

That replaces ~30 lines of `docker_build` / `helm` / `k8s_resource` boilerplate
with one call. Tilt fetches and caches the extension repo automatically;
restart Tilt to pick up updates.

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

## SUSE-AppCo buildpacks (future)

When the SUSE-AppCo buildpacks land, override the builder:

```python
suse_app(..., builder_image='registry.suse.com/rda/builder:latest')
```

## License

Apache-2.0
