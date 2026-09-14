# `ε` gürültü tabanından — G2'nin son açık halkası

Üretim: `plan2_kerr/noise_floor.py` · Testler: `python -m tests.plan2_kerr.run_tests` (123/123)
Karar kaydı: [2026-09-14-retention-noise-floor](../../docs/decisions/2026-09-14-retention-noise-floor.md)

## 0. Sonuç

`ε = 1/e` **iki-üç mertebe fazla katıymış.** Ölçülen taban SNR'a göre
`1e-4` ile `1e-3` arasında. Kabul edilen çalışma değeri **`ε = 1e-2`**.

Kilitli `8 slot × 4 port` readout'ta `Q_i` talebi **3.89e6 → 8.44e5**,
kayıp bütçesi **0.091 → 0.417 dB/cm**.

## 1. Neden ölçüm

`Q_floor ∝ 1/ln(1/ε)`. `1/e` ile `0.01` arasındaki fark 4.6 kat Q demek —
"erişilemez" ile "rahat" arasındaki fark. Bu ağırlıkta bir sayı tercih olarak
kalamaz.

## 2. Kurulum

1. **İdeal readout'un özellik seti:** tek kutuplu kavite gibi sönen gecikme
   tapları. Genlik `r^k`, `r = ε^(1/2m)` — çünkü `ε` *enerji* üzerinde
   tanımlı, tap ise genlik taşıyor. Tüm ikili çarpımlarla genişletildi.
2. **Tespit gürültüsü:** fotodiyot + TIA + ADC. Shot `√(2qI B)`, termal
   `i_n√B`, kuantizasyon `FS/2^bits/√12`, karelerin toplamı.
3. **Aynı değerlendirme:** aynı ridge, aynı dev seed'ler, aynı split.

Varsayılan zincir (2.5 mW/port, R=1 A/W, B=50 GHz, TIA 20 pA/√Hz, 8 bit):
**SNR = 130 (42 dB), shot-noise sınırlı.**

## 3. Ölçüm

30 tap, kuadratik oracle, gürültü dahil, medyan dev NMSE:

| retention@10 | 1e-1 | 1e-2 | 5e-3 | 2e-3 | 1e-3 | 5e-4 | 2e-4 | 1e-4 | 5e-5 | 1e-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| NMSE | 0.0109 | 0.0141 | 0.0173 | 0.0223 | 0.0257 | 0.0286 | 0.0335 | 0.0380 | 0.0432 | 0.0574 |

Eğri `ε ≈ 0.05`'e kadar tamamen düz; altında yavaşça bozuluyor.
Geliştirme kapısı (medyan `< 0.04`) **`1e-4`**'te kırılıyor.

### SNR duyarlılığı

| SNR | 1e-1 | 1e-2 | 1e-3 | 1e-4 | 1e-5 | ε_min |
|---|---|---|---|---|---|---|
| 130 | 0.0109 | 0.0141 | 0.0257 | 0.0380 | 0.0574 | 1e-4 |
| 50 | 0.0119 | 0.0148 | 0.0261 | 0.0383 | 0.0577 | 1e-4 |
| 20 | 0.0168 | 0.0189 | 0.0285 | 0.0404 | 0.0594 | 1e-3 |
| 10 | 0.0282 | 0.0288 | 0.0357 | 0.0468 | 0.0652 | 1e-3 |
| 5 | 0.0529 | 0.0522 | 0.0554 | 0.0660 | 0.0840 | — |

SNR 5'te hiçbir `ε` kapıyı geçirmiyor: sınır artık `ε` değil SNR.
Referans: port gücü 10× düşerse (0.25 mW) SNR 25'e iner; ADC 8→6 bit
olursa SNR 52'ye iner.

## 4. Kabul edilen değer ve neden marj var

**`ε = 1e-2`**: ölçülen tabanın en az bir mertebe üstünde, tüm makul SNR
aralığında geçerli, `1/e`'ye göre ~36 kat gevşek.

Marj gerekli çünkü türetimdeki oracle'ın **495 özelliği** var, bizim
bütçemiz **32**. Ölçülen `ε_min` mükemmel bir readout için bilginin kaybolduğu
nokta — yani **gerekli koşul, yeterli değil.** Gerçek cihaz daha fazlasını
isteyecek; **P3 bunu gerçek modelle yeniden ölçmek zorunda.**

## 5. Terk edilen kapalı form

Önce analitik yol denendi:

```
ε ≥ corr(y, s) / ( SNR · √β ),   s = γ·u[t-9]·u[t]
```

Ölçülen `corr = 0.019` → `ε_min = 1.5e-3`. **Kullanılmadı:** `corr(y,s)`
yanlış istatistik. NARMA-10'un varyansı özyinelemeli kısımda taşınıyor ve o
*daha fazla* bellek istiyor; bu yol gereksinimi iyimser tarafa kaydırıyor.
Fonksiyon kodda çapraz kontrol olarak duruyor, docstring'i eşik belirlemekte
kullanılmamasını söylüyor.

## 6. Yan bulgu: NARMA-10 aslında ~25–30 tap istiyor

Retention = 1, gürültüsüz, kuadratik oracle:

| tap | 12 | 16 | 20 | 25 | 30 |
|---|---|---|---|---|---|
| özellik | 90 | 152 | 230 | 350 | 495 |
| NMSE | 0.1601 | 0.0749 | 0.0465 | 0.0194 | 0.0108 |

"NARMA-**10**"daki 10 özyineleme mertebesidir, görevin istediği giriş belleği
değil. Üstel kuyruk bunu zaten taşıdığından `m = 10` tanımı bozulmuyor.

## 7. Sınırlar

- `DetectionChain` girdilerinin **hepsi `unresolved`** (P1).
- Oracle gerçek cihaz değil; `ε_min` gerekli koşul.
- Tek bir tap-sönüm modeli (tek kutuplu). İki halkalı bir cihazda iki zaman
  sabiti olur ve bu ayrı bir süpürme gerektirir.
- Hiçbir fiziksel kapı geçilmedi.
