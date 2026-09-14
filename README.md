# Kerr Ring Reservoir

Erişilebilir optik güçte, **görev için tasarlanmış** nonlinear halka reservoir
araştırması. Kanonik karar: [Plan 2 ADR](docs/decisions/2026-09-14-plan2-kerr-reservoir.md).

Bu depo, `Nonlinear-3D-FDTD-Photonic-Reservoir` deposundaki Plan 2 hattının
ayrı çalışma alanıdır. Silikon kurtarma hattı (K0–K5) eski depoda kalır.
Taşıma gerekçesi ve devralınanlar: [migrasyon kaydı](docs/decisions/2026-09-14-repo-migration.md).

## Durum

Hiçbir fiziksel kapı geçilmiş değildir. Devralınan optik parametrelerin
tamamı geri çekilmiştir; bkz. [docs/inherited/OPTICAL-PARAMETER-STATUS.md](docs/inherited/OPTICAL-PARAMETER-STATUS.md).

| Kapı | Konu | Durum |
|---|---|---|
| G0 | Kör-test güvenliği (devralınan bug'lar) | **CLOSED** 2026-09-14 |
| G1 | Mode solver sağlık kontrolü: SiN vs Si `n_eff` yakınsaması | OPEN |
| G2 | Kerr bellek üçgeni: `Q` – `T_sym` – güç fizibilitesi | **CLOSED** 2026-09-14 |
| P0–P6 | Plan 2 ADR aşamaları | OPEN |

G1 ve G2, Plan 2'ye geçmeden önce hattın kendisini sınayan ön kapılardır;
ikisi de 0 FC. Ayrıntı: [BACKLOG.md](BACKLOG.md).

G0'ın kapanışı yalnız kör değerlendirme yolunun güvenliğini kapsar; fizik
hakkında hiçbir iddia taşımaz.

## Kabul hedefi

Kilitli tek aday üzerinde 10 kör NARMA-10 seed: medyan NMSE `< 0.05`
**ve** en az 8/10 seed `< 0.05`. Kör suite bu depoda tek kopyadır ve
bir kez tüketilir. Başarısızlık, nedenleriyle birlikte geçerli araştırma
çıktısıdır.

## Yapı

- `benchmarks/narma10_np/` — kilitli NARMA-10 benchmark, aday kilidi ve kör scorer
- `manifests/narma10/` — dev/kör seed hash manifestleri
- `docs/decisions/` — bu depoda alınan kararlar
- `docs/inherited/` — eski depodan devralınan kanıt ve geri çekme kayıtları (tarihçe, talimat değil)
- `reports/FLEXCREDIT-LEDGER.md` — ortak bütçe defteri
- `plan2_kerr/` — G2 bellek üçgeni modeli ve tarama CLI'ı
- `studies/` — hat çalışma alanları ve raporlar

## Çalıştırma

```bash
python -m tests.narma10_np.run_tests    # benchmark + kör yol güvenliği (122)
python -m tests.plan2_kerr.run_tests    # G2 bellek üçgeni (41)
python -m plan2_kerr.screen --boundary  # G2 taraması
```
