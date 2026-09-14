# Backlog

Kanonik sıra: **G0 ✓ → G2 ✓ → G1 ✓ → P0 → P1 …**
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
- Durum: **CLOSED (PASS)** 2026-09-14 — [karar kaydı](docs/decisions/2026-09-14-g1-mode-solver.md),
  [rapor](studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md)
- Kök neden **eksik subpixel ortalaması**. `GridSpec.auto`'nun grid-çizgisi
  yaslaması bağımsız bir hata değil, bu eksikliğin yükselteci.
- Subpixel açıkken dört kapı da, her iki kesitte, her iki grid'de geçti:
  Si yayılımı %1.214 → %0.107; auto grid öteleme duyarlılığı 5.9e-03 → 1.1e-15.
- Kontrast hipotezi kısmen yanlış çıktı: hatanın büyüklüğünü belirliyor,
  fizibiliteyi değil. **Plan 2'nin platform değişimi gerekçelenmiyor.**
- Ortam `tidy3d==2.11.2`'ye sabitlendi; 2.12.0'ın Windows wheel'i yeniden
  dağıtılamaz `libomp140.x86_64.dll` istiyor. Sistem değişikliği yapılmadı.
- Kanıt: `tests/fdtd/` 40/40; `reports/g1/*.json` (4 koşu). 0 FC.
- Geri alınan hüküm: "tüm yerel mode solver kullanılamaz" yanlıştı.

## [G2] Kerr bellek üçgeni
- Sahip: Claude
- Durum: **CLOSED** 2026-09-14 — [karar kaydı](docs/decisions/2026-09-14-g2-memory-triangle.md),
  [rapor](studies/plan2-kerr/MEMORY-TRIANGLE.md)
- Sonuç: `Q_floor = m·ω₀·N/(ln(1/ε)·B)`, malzemeden bağımsız. Nominal Plan 2
  ayarında (m=10, N=20, B=50 GHz, ε=1/e) `Q_L ≥ 4.86e6`, yani `≤0.036 dB/cm`.
  Si₃N₄ ve AlGaAsOI adaylarının ikisinde de bölge **boş**; ikisi de ~7 slot
  veya ~3.6 sembol derinlik taşıyabiliyor.
- Kanıt: `tests/plan2_kerr/` 41/41; `python -m plan2_kerr.screen --boundary`.
- Açık halka **KAPANDI** 2026-09-14: `ε` gürültü tabanından ölçüldü
  ([karar](docs/decisions/2026-09-14-retention-noise-floor.md)); `1/e` iki-üç
  mertebe fazla katıymış, çalışma değeri `1e-2`. `Q_i` talebi 3.89e6 → 8.44e5.
- Hâlâ açık: termal kayma `α_abs` ve `R_th` olmadan hesaplanamıyor (P1).

## [SLOT] Slot/port bütçesi kararı
- Sahip: Claude (analiz); karar Hasan
- Durum: **KİLİTLİ** 2026-09-14 — 8 slot × 4 port = 32 özellik (Hasan) —
  [karar kaydı](docs/decisions/2026-09-14-slot-count.md),
  [rapor](studies/plan2-kerr/SLOT-DECISION.md)
- `Q_floor` yalnız slota bağlı, porta değil: slot ↓ + port ↑ tek tutarlı hamle.
- Özellik hedefi 30 (P3'ün gerçekçi fizik sonucu). ESN referansı 300'de geçiyor;
  bu bir taban değil, gereken ×10 özellik-verimliliğinin ölçüsü.
- Seçilen: **8 slot × 4 port = 32 özellik**; `Q_i ≥ 3.89e6`, kayıp ≤ 0.091 dB/cm,
  `T_sym = 160 ps`. Plan 2 ADR §4 buna göre değiştirildi (özgün metin korundu).
- Tek doğru kaynak `plan2_kerr/readout_contract.py`; sayılar modelden türetiliyor.
- Açık: portların **bağımsızlığı** P2'de kontrol edilecek.

## [P0] Araştırma ve benchmark sınırı — 0 FC
- Sahip: Claude
- Durum: **CLOSED** 2026-09-14
- Teslimat: `studies/plan2-kerr/` altında BENCHMARK-PROTOCOL.md ve
  PLATFORM-EVIDENCE.md (biçim); `plan2_kerr/readout_contract.py` (kilitli readout);
  `plan2_kerr/provenance.py` (deney kimliği, araç sürümleri, git durumu,
  append-only kayıt, hash doğrulama).
- Kanıt: `plan2-kerr-P0-0001` kaydı yazıldı ve `provenance verify` geçiyor;
  `tests/plan2_kerr/` 90/90.
- Sınır: fizik hakkında hiçbir şey sabitlemez. Malzeme girdileri `unresolved`.

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
- İş ve kabul: Plan 2 ADR §7 (64 ön kayıtlı senaryo, ≥%90'ında beş-seed medyan <0.05).
- **Senaryo tasarımı başladı:** [P5-SCENARIO-DESIGN.md](studies/plan2-kerr/P5-SCENARIO-DESIGN.md)
  (TASLAK), kayıt `plan2-kerr-P5-0001`, ham veri `reports/tolerance/geometry-sensitivity.json`.
- Ölçülen (EM-supported, G1 solver, subpixel açık): `dλ/dw` Si 894.2 pm/nm,
  SiN 92.8 pm/nm; `dλ/dh` Si 1948.1, SiN 190.7. Çalışma `Q_L`'de 1 nm genişlik
  hatası SiN'de **25.3 linewidth**, Si'de 243.6.
- Sonuçlar: (a) `ε` gevşemesi toleransı 4.6 kat rahatlatıyor; (b) buna rağmen
  aktif trim mimarinin parçası, opsiyon değil; (c) SiN Si'den ~9.6 kat az
  hassas — G1'in veremediği **fiziksel** platform argümanı.
- **Gap → `κ` ölçüldü** (`plan2-kerr-P5-0003`): parity ile seçilmiş supermode,
  `L_d` Si 117.7 nm / SiN 185.5 nm, `|d ln κ/dg|` Si 0.85 %/nm / SiN 0.54 %/nm.
  Eski hattın "κ altı hanede sabit" bulgusu selector hatasıymış; burada κ
  150→300 nm'de Si'de 3.6, SiN'de 2.2 kat düşüyor.
- Tolerans sıralaması: ±10 nm gap → `Q_e`'de ~%11–18; 1 nm genişlik →
  25 linewidth rezonans kayması. **Baskın risk rezonans hizalaması, kuplaj değil.**
- Dondurma için kalan: P1 proses/malzeme aralıkları, P2/P3 çalışma noktası.
- Trim bütçesi hesaplanamıyor: termo-optik ayar verimliliği `unresolved` (P1).

## [P6] 3B EM ve nihai kör test
- Durum: OPEN; bağımlılık P5, B25
- İş ve kabul: Plan 2 ADR §8.

## [B25] Tarihsel bütçe kararı
- Durum: OPEN — yeni ücretli solve bloke
- Sahip: kayıt Claude, karar Hasan
- İş: geçmiş 79.0726 FC harcamanın doğrulama payı dökümü ve istisna önerisi.
