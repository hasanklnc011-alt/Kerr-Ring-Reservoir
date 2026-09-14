import json, sys
sys.path.insert(0, ".")
from fdtd.modes.environment import require_local_subpixel
from fdtd.modes.cross_sections import SI_450x220 as CS
from fdtd.modes.solver import SolveSettings, solve
from fdtd.modes.selection import select_te_core_mode
require_local_subpixel()
FRACS = (0.0, 0.25, 0.5, 0.75)
rows = []
for spw in (16, 20, 26, 32, 40):
    st = SolveSettings(steps_per_wvl=spw, num_modes=4, pad_x_um=2.0, pad_z_um=2.0)
    dl = st.grid_step_um(CS)
    vals = []
    for f in FRACS:
        vals.append(select_te_core_mode(solve(CS, st, z_offset_um=f*dl)).n_eff)
    swing = max(vals) - min(vals)
    mean = sum(vals)/len(vals)
    rows.append({"spw": spw, "dl_nm": dl*1e3, "n_eff": vals,
                 "swing": swing, "mean": mean})
    print(f"R: spw={spw:3d} dl={dl*1e3:6.2f}nm swing={swing:.4e} mean={mean:.9f} "
          f"vals={[round(v,9) for v in vals]}", flush=True)
for a, b in zip(rows, rows[1:]):
    r_dl = a["dl_nm"]/b["dl_nm"]
    r_sw = a["swing"]/b["swing"] if b["swing"] else float('nan')
    order = (__import__('math').log(r_sw)/__import__('math').log(r_dl)) if r_sw==r_sw and r_sw>0 else float('nan')
    print(f"R: {a['spw']}->{b['spw']}: dl x{r_dl:.3f}, swing x{r_sw:.3f} -> mertebe {order:.2f}", flush=True)
print(f"R: offset-ortalamasi son iki mesh farki = {abs(rows[-1]['mean']-rows[-2]['mean']):.3e}", flush=True)
json.dump(rows, open("reports/g1/alignment-study.json","w"), indent=2)
