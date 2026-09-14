# Backlog

Kanonik sıra: **G0 ✓ → G2 ✓ → G1 (kök neden ✓, kapı açık) → P0 → P1 …**
Kararlar: [Plan 2 ADR](docs/decisions/2026-09-14-plan2-kerr-reservoir.md),
[migrasyon](docs/decisions/2026-09-14-repo-migration.md). Geçmiş: `BACKLOGLOG.md`.

## [G0] Kör-test güvenliği
- Sahip: Claude (kod/test)
- Durum: **CLOSED** 2026-09-14 — [karar kaydı](docs/decisions/2026-09-14-g0-blind-test-safety.md)
- Sonuç: kilit v2 (entry point + paket hash'leri + readout sözleşmesi), baseline
  yasağı, skordan önce atomik tüketim, dışlayıcı süreç kilidi, `run_id`+checkpoint
  kurtarma, CLI'dan skorlama parametrelerinin kaldırılması.
- Kanıt: `tests/narma10_np/` 122/122; `preflight` 8/8.

## [G1] Mode solver sağlığı — Si vs SiN
- Sahip: Claude
- Durum: **KISMEN KAPALI** 2026-09-14 — [karar kaydı](docs/decisions/2026-09-14-g1-mode-solver.md),
  [rapor](studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md)
- Kök neden bulundu: `GridSpec.auto` grid çizgilerini yapı sınırlarına yaslıyor;
  subpixel yokken arayüz atamasını `1e-12 µm` öteleme topluca çeviriyor. Uniform
  grid'de etki kayboluyor ve `n_eff` monoton yakınsıyor. Mode solver reddedilmemeli.
- Kontrast ikincil: yayılımı 3.8 kat ölçekliyor ama auto grid'de etki SiN'de de var.
  **Plan 2'nin platform değişimi bu bulguyla gerekçelenmiyor.**
- Kanıt: `tests/fdtd/` 36/36; `reports/g1/*.json`.
- **AÇIK:** kapı kapanmadı. `libomp140.x86_64.dll` (LLVM OpenMP) makinede yok,
  bu yüzden local subpixel çalışmıyor ve iki koşu da `gate_valid: false`.
  Sıradaki adım: DLL'i güvenilir kaynaktan edin (Hasan'ın ortam kararı), sonra
  aynı merdiveni subpixel ile koş.

## [G2] Kerr bellek üçgeni
- Sahip: Claude
- Durum: **CLOSED** 2026-09-14 — [karar kaydı](docs/decisions/2026-09-14-g2-memory-triangle.md),
  [rapor](studies/plan2-kerr/MEMORY-TRIANGLE.md)
- Sonuç: `Q_floor = m·ω₀·N/(ln(1/ε)·B)`, malzemeden bağımsız. Nominal Plan 2
  ayarında (m=10, N=20, B=50 GHz, ε=1/e) `Q_L ≥ 4.86e6`, yani `≤0.036 dB/cm`.
  Si₃N₄ ve AlGaAsOI adaylarının ikisinde de bölge **boş**; ikisi de ~7 slot
  veya ~3.6 sembol derinlik taşıyabiliyor.
- Kanıt: `tests/plan2_kerr/` 41/41; `python -m plan2_kerr.screen --boundary`.
- Açık: `ε` gürültü modeli olmadan keyfî (P2'ye taşındı); termal kayma
  `α_abs` ve `R_th` olmadan hesaplanamıyor (P1/K2a).

## [P0] Araştırma ve benchmark sınırı — 0 FC
- Durum: OPEN; bağımlılık G0
- İş ve kabul: Plan 2 ADR §2. Teslimat `studies/plan2-kerr/` altında
  `README.md`, `BENCHMARK-PROTOCOL.md`, `PLATFORM-EVIDENCE.md`.
- Not: dokümantasyon yayımlamak tek başına P0 teknik kabulü değildir.

## [P1] Malzeme ve güç fizibilitesi — 0 FC
- Durum: OPEN; bağımlılık G2, P0
- İş ve kabul: Plan 2 ADR §3. Her satır birim, birincil kaynak, dalga boyu,
  sıcaklık, proses/geometri uyumu ve kabul statüsü taşır.

## [P2] Dinamik çekirdek — 0 FC
- Durum: OPEN; bağımlılık P0
- İş ve kabul: Plan 2 ADR §4. Analitik limit, enerji, sönüm ve zaman
  yakınsaması testleriyle.

## [P3] Nonlinearlik ve bellek bölgesi — 0 FC
- Durum: OPEN; bağımlılık G1, G2, P1, P2
- İş ve kabul: Plan 2 ADR §5.

## [P4] Halka geometrisi — 0 FC
- Durum: OPEN; bağımlılık G1, P3
- İş ve kabul: Plan 2 ADR §6.
- Açık soru: halka uzayı parametrik olduğundan adjoint/Angler'ın getirisi
  gösterilmelidir. Parametrik tarama (FEMwell + CMT + SAX) yeterliyse
  Angler eklenmez.

## [P5] Dayanıklılık — 0 FC
- Durum: OPEN; bağımlılık P3, P4
- İş ve kabul: Plan 2 ADR §7.

## [P6] 3B EM ve nihai kör test
- Durum: OPEN; bağımlılık P5, B25
- İş ve kabul: Plan 2 ADR §8.

## [B25] Tarihsel bütçe kararı
- Durum: OPEN — yeni ücretli solve bloke
- Sahip: kayıt Claude, karar Hasan
- İş: geçmiş 79.0726 FC harcamanın doğrulama payı dökümü ve istisna önerisi.
