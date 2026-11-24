---
name: verify-direct-play-scores
description: "Verify Xbox Direct Play custom-format score algebra (HARD_REJECT cannot clear MIN_FORMAT_SCORE=0). Use when changing playback_compat, recyclarr.yml scores, or min_format_score."
---

# Verify Direct Play scores

## When

Any change to `compose_files/scripts/stack_policy/playback_compat.py`, `compose_files/scripts/stack_policy/score_model.py`, or scored ids / `min_format_score` in `compose_files/recyclarr/recyclarr.yml`.

## Property

`accept iff sum(scores) >= MIN_FORMAT_SCORE`. Every negative term this policy assigns is `HARD_REJECT` (-10000). With `MIN_FORMAT_SCORE = 0`, a single reject cannot pass unless bonuses sum to at least +10000.

Past bug: X2 (2003) as DTS-HD MA (-10000) + HDR (+500) = -9500 cleared `min_format_score: -9999`.

## Run

```bash
cd compose_files/scripts
PYTHONPATH=. python3 -m unittest test_stack_policy.PlaybackCompatTests -v
```

## Broken-variant proof

Set `MIN_FORMAT_SCORE = -9999` in `playback_compat.py`. `test_bonuses_cannot_lift_a_hard_reject_over_minimum` must fail. Restore to `0`.

## Coverage record

- Code: `playback_compat.score_map`, `score_model.is_accepted`, Recyclarr `min_format_score`
- Sync commit: update after intentional score changes only
- Bounds: arithmetic over listed scores; does not model TRaSH Guide groups synced outside this repo's YAML assigns
