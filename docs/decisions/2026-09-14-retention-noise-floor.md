# Retention `ε` gürültü tabanından ölçüldü; `1/e` terk edildi

- Durum: **KAPALI**, 2026-09-14. G2'nin açık bırakılan tek zayıf halkası.
- Sahip: Claude (kod/test).
- Rapor: [studies/plan2-kerr/RETENTION-NOISE-FLOOR.md](../../studies/plan2-kerr/RETENTION-NOISE-FLOOR.md)
- Üst karar: [G2](2026-09-14-g2-memory-triangle.md)

## Sorun

`Q_floor = m·ω₀·N / (ln(1/ε)·B)`. `ε = 1/e` bir yer tutucuydu ve kaldıracı
çok büyüktü: `0.01`'e gevşetmek Q talebini 4.6 kat düşürüyor. Bu ağırlıkta bir
sayı tercih olarak kalamaz.

## Yöntem — ölçüm, türetim değil

1. **İdeal** bir readout'un göreceği özellik seti kuruldu: tek kutuplu bir
   kavitenin genlik sönümüyle zayıflatılan gecikme tapları, `m = 10`'da
   **enerji** retention'ı tam olarak `ε` olacak şekilde normalize edildi,
   tüm ikili çarpımlarla genişletildi.
2. Modellenmiş bir fotodiyot + TIA + ADC zincirinin SNR'ında örnek başına
   tespit gürültüsü eklendi (`DetectionChain`).
3. Aynı ridge, aynı dev seed'ler, aynı split; `ε` süpürülüp geliştirme
   kapısının (medyan `< 0.04`) kırıldığı nokta bulundu.

## Sonuç

| SNR | kapıyı geçen en küçük retention |
|---|---|
| ≥ 50 | `1e-4` |
| 10–20 | `1e-3` |
| 5 | hiçbiri (sınır artık SNR'ın kendisi) |

**`ε = 1/e` iki-üç mertebe fazla katıymış.**

Kabul edilen çalışma değeri: **`ε = 1e-2`** — ölçülen tabanın en az bir
mertebe üstünde, tüm makul SNR aralığında, ve `1/e`'ye göre ~36 kat gevşek.

### Fiziksel sonucu

Kilitli `8 slot × 4 port` readout'ta:

| | `ε = 1/e` | `ε = 1e-2` |
|---|---|---|
| `Q_floor` | 1.94e6 | **4.22e5** |
| `Q_i` gerekli | 3.89e6 | **8.44e5** |
| maks kayıp (`n_g=2.0`) | 0.091 dB/cm | **0.417 dB/cm** |

Bu, kaynaklı AlGaAsOI cihazının (`Q_i = 3.52e6`) **4 kat üstünde marj**
bırakıyor ve SiN tarafını rahatlatıyor.

## Bu bir alt sınır, üst sınır değil

Türetimde kullanılan oracle 495 özelliğe sahip; bizim bütçemiz 32. Yani
ölçülen `ε_min` **gerekli koşuldur, yeterli değil**: mükemmel bir readout
için bile bilginin kaybolduğu nokta. Gerçek 32 özellikli cihaz daha fazlasını
isteyecek ve bunu **P3 gerçek modelle yeniden ölçmek zorunda.** `1e-2`
çalışma değeri bu belirsizlik için marj taşıyor.

## Terk edilen yol — kayda geçirildi

Önce kapalı form denendi: `ε ≥ corr(y,s) / (SNR·√β)`, `s` NARMA-10'un açık
`γ·u[t-9]·u[t]` terimi. Ölçülen `corr = 0.019` ve bu `ε_min = 1.5e-3` veriyordu.

**Kullanılmadı.** `corr(y,s)` yanlış istatistik: NARMA-10'un varyansı
özyinelemeli kısımda taşınıyor ve o *daha fazla* bellek istiyor, dolayısıyla
bu yol gereksinimi iyimser tarafa kaydırıyor. Fonksiyon çapraz kontrol olarak
kodda duruyor ve docstring'i eşik belirlemek için kullanılmamasını söylüyor.

## Yan bulgu

Kuadratik bir oracle NARMA-10'u çözebilmek için **~25–30 giriş tapı**
istiyor; 12 tapta NMSE 0.16'da düzleşiyor. "NARMA-**10**"daki 10 özyineleme
mertebesidir, görevin istediği giriş belleği değil. Süpürmedeki üstel kuyruk
bunu zaten taşıdığından `m`'ye ayrı bir düzeltme gerekmiyor.

## Açık kalanlar

- `DetectionChain` girdilerinin hepsi `unresolved` (P1): port gücü,
  modülasyon derinliği, responsivity, TIA gürültü yoğunluğu, ADC bit sayısı.
  Varsayılan zincir 42 dB SNR veriyor ve shot-noise sınırlı; 10× daha düşük
  güçte SNR 25'e düşüyor ve `ε_min` `1e-3`'e çıkıyor.
- SNR ≈ 5'in altında `ε` ne olursa olsun kapı geçilmiyor. Bu ayrı bir
  fizibilite koşulu ve P1'in güç bütçesine bağlı.
- P3, `ε`'u gerçek 32 özellikli modelle yeniden doğrulayacak.

## Kanıt

`plan2_kerr/noise_floor.py`; `tests/plan2_kerr/` 123/123. Dev seed'ler,
kör suite'e dokunulmadı, 0 FC.
