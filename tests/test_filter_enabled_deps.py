#!/usr/bin/env python3
"""
Test the filter_enabled_deps logic (#16).

The real filter_enabled_deps.py is embedded in the Tiltfile as a Starlark
string literal — it cannot be imported directly. This test reimplements
the core filtering logic (enabled_charts + dep filtering + multi-instance
alias expansion) and validates it against representative inputs.

Three behaviours tested:
  1. Basic filtering: 16 deps in Chart.yaml, 2 services enabled
     (postgresql, redis) => only those 2 deps are kept.
  2. Multi-instance aliasing (#24): two grafana bindings expand to two
     aliased deps (grafana-metrics, grafana-dashboards).
  3. Existing aliases preserved: dex-idp aliased as dex stays intact.

Usage: python3 test_filter_enabled_deps.py
       chmod +x && ./test_filter_enabled_deps.py
"""
import os
import sys
import tempfile
import shutil

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML not installed; pip3 install pyyaml\n")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Reimplemented core logic (mirrors the Tiltfile-embedded script exactly).
# ---------------------------------------------------------------------------

SKIP_TOP = {
    "suse-library", "global", "image", "ingress",
    "imagePullSecrets", "resources", "probes", "metrics",
    "podAnnotations", "service", "name", "replicas",
    "port", "apiVersion", "kind",
}


def enabled_charts(values_files):
    """Union the chart names with .enabled=true across all values files."""
    enabled = set()
    for path in values_files:
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        sl = data.get("suse-library")
        if isinstance(sl, dict):
            for name, sub in sl.items():
                if isinstance(sub, dict) and sub.get("enabled") is True:
                    enabled.add(name)
            services = sl.get("services") or []
            if isinstance(services, list):
                type_counts = {}
                for entry in services:
                    if isinstance(entry, dict) and entry.get("type"):
                        t = entry["type"]
                        type_counts[t] = type_counts.get(t, 0) + 1
                for entry in services:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("enabled", True) is False:
                        continue
                    chart_type = entry.get("type")
                    binding = entry.get("binding", "")
                    if chart_type:
                        enabled.add(chart_type)
                        if type_counts.get(chart_type, 0) > 1 and binding:
                            enabled.add(chart_type + "-" + binding)
        for name, sub in data.items():
            if name in SKIP_TOP:
                continue
            if isinstance(sub, dict) and sub.get("enabled") is True:
                enabled.add(name)
    return enabled


def filter_deps(full_deps, enabled, values_files):
    """Filter and expand deps based on enabled charts and multi-instance aliases."""
    expanded_deps = list(full_deps)
    multi_aliases = {}

    for path in values_files:
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        sl = data.get("suse-library")
        if not isinstance(sl, dict):
            continue
        services = sl.get("services") or []
        if not isinstance(services, list):
            continue
        type_bindings = {}
        for entry in services:
            if not isinstance(entry, dict):
                continue
            t = entry.get("type", "")
            b = entry.get("binding", "")
            if t and b:
                type_bindings.setdefault(t, []).append(b)
        for t, bindings in type_bindings.items():
            if len(bindings) > 1:
                multi_aliases[t] = [t + "-" + b for b in bindings]

    if multi_aliases:
        new_deps = []
        for d in expanded_deps:
            ename = d.get("alias", d.get("name"))
            if ename in multi_aliases:
                for alias in multi_aliases[ename]:
                    aliased = dict(d)
                    aliased["alias"] = alias
                    aliased["condition"] = alias + ".enabled"
                    new_deps.append(aliased)
            else:
                new_deps.append(d)
        expanded_deps = new_deps

    if not enabled:
        return []
    return [d for d in expanded_deps if d.get("alias", d.get("name")) in enabled]


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

# Representative Chart.yaml with 16 deps (the full catalog).
FULL_CHART_YAML = {
    "apiVersion": "v2",
    "name": "suse-library",
    "version": "0.1.0",
    "dependencies": [
        {"name": "postgresql",     "version": "0.4.4-29.1", "repository": "oci://dp.apps.rancher.io/charts", "condition": "postgresql.enabled"},
        {"name": "redis",          "version": "2.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "redis.enabled"},
        {"name": "prometheus",     "version": "29.0.0",     "repository": "oci://dp.apps.rancher.io/charts", "condition": "prometheus.enabled"},
        {"name": "grafana",        "version": "12.0.0",     "repository": "oci://dp.apps.rancher.io/charts", "condition": "grafana.enabled"},
        {"name": "dex-idp",        "version": "0.24.0",     "repository": "oci://dp.apps.rancher.io/charts", "alias": "dex", "condition": "dex.enabled"},
        {"name": "mariadb",        "version": "0.1.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "mariadb.enabled"},
        {"name": "apache-kafka",   "version": "1.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "apache-kafka.enabled"},
        {"name": "valkey",         "version": "0.11.0",     "repository": "oci://dp.apps.rancher.io/charts", "condition": "valkey.enabled"},
        {"name": "minio",          "version": "5.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "minio.enabled"},
        {"name": "vault",          "version": "0.31.0",     "repository": "oci://dp.apps.rancher.io/charts", "condition": "vault.enabled"},
        {"name": "etcd",           "version": "0.3.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "etcd.enabled"},
        {"name": "nats",           "version": "2.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "nats.enabled"},
        {"name": "opensearch",     "version": "3.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "opensearch.enabled"},
        {"name": "influxdb",       "version": "2.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "influxdb.enabled"},
        {"name": "harbor",         "version": "1.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "harbor.enabled"},
        {"name": "apache-airflow", "version": "1.0.0",      "repository": "oci://dp.apps.rancher.io/charts", "condition": "apache-airflow.enabled"},
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  \033[32m✓\033[0m %s" % name)
    else:
        failed += 1
        msg = "  \033[31m✗\033[0m %s" % name
        if detail:
            msg += " — %s" % detail
        print(msg, file=sys.stderr)


def test_basic_filtering():
    """Only enabled services' deps are kept (16 deps, 2 enabled)."""
    tmpdir = tempfile.mkdtemp(prefix="rda-test-filter-")
    try:
        # Write Chart.yaml.full (source of truth).
        chart_yaml_full = os.path.join(tmpdir, "Chart.yaml.full")
        with open(chart_yaml_full, "w") as f:
            yaml.safe_dump(FULL_CHART_YAML, f, default_flow_style=False)

        # Write values.yaml with postgresql + redis enabled.
        values_path = os.path.join(tmpdir, "values.yaml")
        values = {
            "suse-library": {
                "services": [
                    {"type": "postgresql", "binding": "db",    "enabled": True,
                     "auth": {"user": {"password": "dev", "database": "app"},
                              "admin": {"password": "admin"}}},
                    {"type": "redis",      "binding": "cache", "enabled": True,
                     "auth": {"password": "dev"}},
                ],
            },
        }
        with open(values_path, "w") as f:
            yaml.safe_dump(values, f, default_flow_style=False)

        enabled = enabled_charts([values_path])
        full_deps = FULL_CHART_YAML["dependencies"]
        kept = filter_deps(full_deps, enabled, [values_path])

        kept_names = sorted([d.get("alias", d.get("name")) for d in kept])
        report(
            "basic filtering: 16 deps -> 2 kept (postgresql, redis)",
            kept_names == ["postgresql", "redis"],
            "got %s" % kept_names,
        )
        report(
            "basic filtering: enabled set is exactly {postgresql, redis}",
            enabled == {"postgresql", "redis"},
            "got %s" % enabled,
        )
    finally:
        shutil.rmtree(tmpdir)


def test_multi_instance_aliasing():
    """Two grafana bindings expand to two aliased deps (#24)."""
    tmpdir = tempfile.mkdtemp(prefix="rda-test-filter-")
    try:
        values_path = os.path.join(tmpdir, "values.yaml")
        values = {
            "suse-library": {
                "services": [
                    {"type": "grafana", "binding": "metrics",    "enabled": True,
                     "auth": {"admin": {"password": "dev"}}},
                    {"type": "grafana", "binding": "dashboards", "enabled": True,
                     "auth": {"admin": {"password": "dev"}}},
                    {"type": "postgresql", "binding": "db",      "enabled": True,
                     "auth": {"user": {"password": "dev", "database": "app"},
                              "admin": {"password": "admin"}}},
                ],
            },
        }
        with open(values_path, "w") as f:
            yaml.safe_dump(values, f, default_flow_style=False)

        enabled = enabled_charts([values_path])
        full_deps = FULL_CHART_YAML["dependencies"]
        kept = filter_deps(full_deps, enabled, [values_path])

        kept_names = sorted([d.get("alias", d.get("name")) for d in kept])

        # grafana type -> grafana-metrics + grafana-dashboards (aliased)
        report(
            "multi-instance: grafana-metrics alias present",
            "grafana-metrics" in kept_names,
            "got %s" % kept_names,
        )
        report(
            "multi-instance: grafana-dashboards alias present",
            "grafana-dashboards" in kept_names,
            "got %s" % kept_names,
        )
        report(
            "multi-instance: postgresql (single instance) still present",
            "postgresql" in kept_names,
            "got %s" % kept_names,
        )
        report(
            "multi-instance: total kept count is 3 (2 grafana aliases + 1 postgresql)",
            len(kept) == 3,
            "got %d: %s" % (len(kept), kept_names),
        )

        # Verify the aliased deps have correct condition fields.
        for d in kept:
            alias = d.get("alias", d.get("name"))
            if alias.startswith("grafana-"):
                report(
                    "multi-instance: %s condition is %s.enabled" % (alias, alias),
                    d.get("condition") == alias + ".enabled",
                    "got condition=%r" % d.get("condition"),
                )
                # The underlying chart name must still be grafana.
                report(
                    "multi-instance: %s name is still grafana" % alias,
                    d.get("name") == "grafana",
                    "got name=%r" % d.get("name"),
                )
    finally:
        shutil.rmtree(tmpdir)


def test_preserves_existing_aliases():
    """dex-idp aliased as dex stays intact after filtering."""
    tmpdir = tempfile.mkdtemp(prefix="rda-test-filter-")
    try:
        values_path = os.path.join(tmpdir, "values.yaml")
        values = {
            "suse-library": {
                "services": [
                    {"type": "dex", "binding": "auth", "enabled": True,
                     "ingress": {"enabled": True,
                                 "host": "auth.app.localtest.me"}},
                ],
            },
        }
        with open(values_path, "w") as f:
            yaml.safe_dump(values, f, default_flow_style=False)

        enabled = enabled_charts([values_path])
        full_deps = FULL_CHART_YAML["dependencies"]
        kept = filter_deps(full_deps, enabled, [values_path])

        # The dex dep has alias=dex, so the effective name is "dex".
        kept_names = [d.get("alias", d.get("name")) for d in kept]
        report(
            "existing alias: dex is in kept deps",
            "dex" in kept_names,
            "got %s" % kept_names,
        )

        # The underlying chart name must remain dex-idp.
        dex_dep = [d for d in kept if d.get("alias") == "dex"]
        report(
            "existing alias: underlying name is dex-idp",
            len(dex_dep) == 1 and dex_dep[0].get("name") == "dex-idp",
            "got %s" % ([d.get("name") for d in dex_dep],),
        )

        # Only 1 dep should be kept.
        report(
            "existing alias: exactly 1 dep kept",
            len(kept) == 1,
            "got %d" % len(kept),
        )
    finally:
        shutil.rmtree(tmpdir)


def test_disabled_services_excluded():
    """Services with enabled=false are not kept."""
    tmpdir = tempfile.mkdtemp(prefix="rda-test-filter-")
    try:
        values_path = os.path.join(tmpdir, "values.yaml")
        values = {
            "suse-library": {
                "services": [
                    {"type": "postgresql", "binding": "db", "enabled": True,
                     "auth": {"user": {"password": "dev", "database": "app"},
                              "admin": {"password": "admin"}}},
                    {"type": "redis", "binding": "cache", "enabled": False,
                     "auth": {"password": "dev"}},
                ],
            },
        }
        with open(values_path, "w") as f:
            yaml.safe_dump(values, f, default_flow_style=False)

        enabled = enabled_charts([values_path])
        full_deps = FULL_CHART_YAML["dependencies"]
        kept = filter_deps(full_deps, enabled, [values_path])

        kept_names = sorted([d.get("alias", d.get("name")) for d in kept])
        report(
            "disabled excluded: only postgresql kept",
            kept_names == ["postgresql"],
            "got %s" % kept_names,
        )
        report(
            "disabled excluded: redis not in enabled set",
            "redis" not in enabled,
            "enabled=%s" % enabled,
        )
    finally:
        shutil.rmtree(tmpdir)


def test_empty_services():
    """No services enabled => no deps kept."""
    tmpdir = tempfile.mkdtemp(prefix="rda-test-filter-")
    try:
        values_path = os.path.join(tmpdir, "values.yaml")
        values = {"suse-library": {"services": []}}
        with open(values_path, "w") as f:
            yaml.safe_dump(values, f, default_flow_style=False)

        enabled = enabled_charts([values_path])
        full_deps = FULL_CHART_YAML["dependencies"]
        kept = filter_deps(full_deps, enabled, [values_path])

        report(
            "empty services: no deps kept",
            len(kept) == 0,
            "got %d" % len(kept),
        )
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print("== filter_enabled_deps logic tests ==\n")

    test_basic_filtering()
    test_multi_instance_aliasing()
    test_preserves_existing_aliases()
    test_disabled_services_excluded()
    test_empty_services()

    print("\n-- %d passed, %d failed --" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
