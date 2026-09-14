# G1 mode-diagnostic environment

Isolated and version-locked. Never install these into the system Python.

```bash
python -m venv .venv-mode-211
./.venv-mode-211/Scripts/python.exe -m pip install -r requirements/g1-mode-win-py314.lock.txt
./.venv-mode-211/Scripts/python.exe -m fdtd.modes env      # must say AVAILABLE
```

`env` proves local subpixel empirically: it runs the same small high-contrast
solve with the flag off and on and requires the answer to change. A flag that
is accepted but ignored fails the gate.

## Why 2.11.2 and not 2.12.0

On this machine (Windows 11, Python 3.14.7) `tidy3d-extras==2.12.0` installs
and imports, but local subpixel fails at solve time:

```
GencoeffsSubprocessError: Local subpixel gencoeffs worker failed with exit code 1
ImportError: DLL load failed while importing _isolated_extension
```

The cause was pinned by reading the PE import tables of the shipped
extensions, recorded 2026-09-14:

| wheel | native modules | extra dependency |
|---|---|---|
| 2.12.0 | `extension`, `_isolated_extension` | `_isolated_extension` needs `libomp140.x86_64.dll` |
| 2.11.x | `extension` only | `VCOMP140.DLL` |

`libomp140.x86_64.dll` is the **LLVM** OpenMP runtime. Microsoft ships it only
inside Visual Studio under
`VC\Redist\MSVC\<ver>\debug_nonredist\x64\Microsoft.VC142.OpenMP.LLVM`, and
that copy is explicitly **non-redistributable** (the `/openmp:llvm` switch is
experimental). There is no Visual Studio on this machine, and a loose DLL from
a download site is not an acceptable source for a numerics gate.

`VCOMP140.DLL` is Microsoft's own OpenMP runtime, part of the ordinary VC++
redistributable, and it is already present at `C:\Windows\System32`. So the
2.11.x wheel works with no system change at all.

Pinning 2.11.2 therefore costs nothing here and keeps the environment
self-contained. If a later tidy3d is needed for cloud work, keep that in a
separate venv; this one exists only for local mode diagnostics.
