# Canonical NARMA-10 benchmark

Deterministic local NARMA-10 benchmark skeleton (charter phase 2). No Tidy3D,
no cloud, no network.

> **Astra kararı (2026-09-10):** Bu NumPy uygulaması kanoniktir. Eşzamanlı
> üretilen standart-kütüphane çoğaltısı kaldırıldı; seçim gerekçesi,
> `u`/`y` içerik hash'leri, candidate-lock'a bağlanan blind manifesto özeti ve
> aday başına tek seferlik append-only blind ledger kapılarıdır.

## Modules

| module | purpose |
| --- | --- |
| `config.py` | immutable benchmark constants (coeffs, sequence layout, seed namespaces, acceptance target) |
| `signals.py` | SHA-256-derived per-trial seeds, `Uniform[0,0.5)` drive, classic NARMA-10 recurrence, array hashing |
| `dataset.py` | `Narma10Trial` with washout/train/test slices + finiteness checks |
| `manifest.py` | build / write / verify SHA-256 seed+data manifests, `manifest_digest` |
| `metrics.py` | `nmse` / `nrmse` / `median_nmse` with strict finiteness guards |
| `readout.py` | closed-form ridge regression readout + delay embedding |
| `evaluate.py` | `evaluate_states` seam for the future reservoir + `score_spec` acceptance logic |
| `candidate_lock.py` | v2 candidate package lock: entry point, per-file source hashes, readout contract, fail-closed `guard_blind_evaluation` |
| `blind_ledger.py` | atomic single-attempt ledger: reserve-before-scoring, exclusive process lock, checkpointed recovery |
| `blind_run.py` | the one blind evaluation path (guard -> lock -> reserve -> locked scorer -> complete) |
| `preflight.py` | deterministic read-only preflight: provenance, manifest verify/digests, finite seed counts, candidate-lock status, blind-eval block state |
| `cli.py` | `python -m benchmarks.narma10_np ...` |

## CLI

```
python -m benchmarks.narma10_np preflight            # read-only; exit 0 iff no check FAILs
python -m benchmarks.narma10_np preflight --json      # machine-readable report
python -m benchmarks.narma10_np generate-manifests
python -m benchmarks.narma10_np verify-manifests
python -m benchmarks.narma10_np baseline
python -m benchmarks.narma10_np lock-candidate --id C001 \n    --source-root <dir> --entry-point <module:factory> \n    --slots 20 --ports 2 --description "..."
python -m benchmarks.narma10_np blind-eval --id C001                  # the single attempt
python -m benchmarks.narma10_np blind-eval --id C001 --resume-run <id>  # resume a crashed run
```

## Tests

```
python tests/narma10_np/run_tests.py        # 82 tests, stdlib unittest, no pytest needed
```

## Locked artifacts in this repo

- `manifests/narma10/dev_seeds.sha256.json` — 5 development trials
- `manifests/narma10/blind_seeds.sha256.json` — 10 blind trials

Both **verify** but are **not yet ratified/sealed by Astra**. The blind set must
never be tuned against.
