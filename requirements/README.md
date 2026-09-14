# G1 mode-diagnostic environment

Isolated, version-locked. Never install these into the system Python.

```bash
python -m venv .venv-mode
./.venv-mode/Scripts/python.exe -m pip install -r requirements/g1-mode-win-py314.lock.txt
./.venv-mode/Scripts/python.exe -m fdtd.modes env
```

`env` must report `local subpixel  AVAILABLE` before any G1 gate can be
decided. On this machine (Windows 11, Python 3.14.7) it does **not**:
`tidy3d_extras` installs and `tidy3d_extras.extension` loads, but
`tidy3d_extras._isolated_extension` — the worker that actually computes the
subpixel coefficients — fails with `DLL load failed`.

The cause is pinned: that extension is the only one of the two that imports
`libomp140.x86_64.dll` (LLVM OpenMP runtime), and the DLL is not present
anywhere on the machine. The MSVC runtime (`msvcp140`, `vcruntime140`,
`vcruntime140_1`) is present, so this is specifically the OpenMP runtime.

Import table comparison, recorded 2026-09-14:

| module | extra dependency |
|---|---|
| `extension.cp314-win_amd64.pyd` | (loads) |
| `_isolated_extension.cp314-win_amd64.pyd` | `libomp140.x86_64.dll` |

Resolving this is an environment decision for Hasan, not something to be
worked around: obtaining `libomp140.x86_64.dll` from a trustworthy source
(e.g. the Visual Studio installer's LLVM/clang component) is the clean fix.
Do not download a loose DLL from a random site.
