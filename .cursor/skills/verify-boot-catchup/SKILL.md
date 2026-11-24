---
name: verify-boot-catchup
description: "Verify homelab-setup boot catch-up and Recyclarr side effects, plus the TLA+ downtime model. Use when changing boot mode, catchup, or Recyclarr sync on reboot."
---

# Verify boot catch-up

## When

Changes to `homelab-setup.sh` mode branches, `stack_policy.reconcile`, `stack_policy.catchup`, or `formal/boot_catchup/`.

## Properties

1. Python: `effects_for("boot")` includes catch-up and Recyclarr; forbids queue wipe and qBittorrent restart.
2. TLA+: after `Boot`, every title released within `Lookback` days has a search request (`BootCoversLookback`).

## Run

```bash
PYTHONPATH=compose_files/scripts python3 -m unittest test_stack_policy.ReconcileModeTests -v
bash formal/boot_catchup/run.sh
```

Needs `java` and `tla2tools.jar` (set `TLA2TOOLS_JAR` or use mise `http-tla2tools` 1.7.4).

## Broken-variant proof

`BootCatchupBroken.tla` boots without searching. `run.sh` expects TLC to fail that model, then pass `BootCatchup.tla`.

## Coverage

- Code: `homelab-setup.sh` `main`, `reconcile.effects_for`, catch-up lookback 14
- Sync commit: move forward only after confirming the model still matches boot's call list
- Bounds: two titles, MaxDay 5–20; does not model *arr API failures (`|| true` in the shell)
