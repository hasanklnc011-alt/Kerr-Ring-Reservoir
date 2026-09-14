# Backlog

Kanonik sıra: **G0 (kapandı) → G1 → G2 → P0 → P1 …**
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
- Durum: OPEN
- Bağımlılık: yok (G0 ile paralel yürüyebilir)
- İş: Tek tanı modülü; izole ve sürüm-kilitli ortam; local subpixel zorunlu,
  sessiz fallback yasak. 16/20/26/32 step/λ; Ex/Ey/Ez örnekleri; aynı grid'de
  ±1e-12 µm öteleme testi; TE/çekirdek/parity/örtüşme tabanlı mod seçici
  (en yüksek `n_eff`'e fallback yok). Aynı koşu Si (450×220 nm) ve SiN
  kesitinde tekrarlanır.
- Kabul: öteleme `|Δn_eff| < 1e-5`; son iki mesh `|Δn_eff| < 1e-3`;
  `n_g` değişimi `< %1`; mod örtüşmesi `> 0.99`.
- Karar çıktısı: SiN geçip Si geçmezse kök neden indeks kontrastıdır ve
  platform değişimi gerekçelenir. İkisi de geçmezse araç Plan 2'de
  kullanılamaz; P4 yeniden tasarlanır.

## [G2] Kerr bellek üçgeni
- Sahip: Claude
- Durum: OPEN
- Bağımlılık: yok
- İş: Kerr anlık olduğundan belleğin foton ömründen geldiğini varsayarak
  `Q`, `T_sym`, giriş gücü ve NARMA-10 geçmiş derinliği arasındaki fizibilite
  bölgesini kapalı formda çıkar. Kerr rezonans kayması / linewidth oranını
  kaynaklı `n2` ile tahmin et. Termo-optik kaymayı aynı çalışma noktasında
  yan yana koy. Erişilebilir modülatör/detektör hızı sınırını uygula.
- Kabul: her aday platform için fizibilite bölgesinin boş olup olmadığı
  sayıyla gösterilir; bölge boşsa Kerr-only hattı durur.
- Not: Bu kapı P1 platform taramasından önce gelir; hangi platformun
  aranmaya değer olduğunu belirler.

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
