# 2026-09-13 — Bulundu: bus facet'leri Fabry-Pérot kavitesi kuruyor

- Yapan: Claude Opus 5
- Maliyet: **0 FlexCredit** — analiz zaten ödenmiş `mesh_rung2_data.hdf5` üzerinde
- Açıkladığı belirti: `docs/decisions/2026-09-13-freq-rung-1-evaluation.md` §3

## Belirti

`freq-rung-1`'de rezonans dışında bile gücün `%12–23`'ü ölçülemiyordu ve
baseline 3 nm içinde `0.774 → 0.884` diye eğimliydi. Malzemeler kayıpsız
(`conductivity = 0`) olduğu için bu emilim olamazdı. BOX sızıntısı ve izlenmeyen
drop portu ayrı ayrı elendi (bkz. `2026-09-13-box-leakage-falsified.md`).

## Ölçüm

`mesh-rung-2`'nin tam bandı (`1.50–1.60 µm`, 201 nokta) halka rezonansları
`±0.8 nm` maskelenerek incelendi — kalan 186 nokta:

```
1.50-1.51 um : ort 0.7314   (min 0.5284  max 0.8741)
1.51-1.52 um : ort 0.5931   (min 0.5268  max 0.7533)
1.52-1.53 um : ort 0.7782   (min 0.6401  max 0.8793)
1.53-1.54 um : ort 0.6125   (min 0.5371  max 0.8069)
1.54-1.55 um : ort 0.7336   (min 0.5599  max 0.8833)
1.55-1.56 um : ort 0.6560   (min 0.5462  max 0.8667)
...
tam bant: min 0.5126  max 0.8988  ortalama 0.6883
```

Baseline `0.51` ile `0.90` arasında salınıyor — **`%40` tepe-tepe**. Yerel
maksimumlar: `1.5075, 1.5248, 1.5429, 1.5610, 1.5784, 1.5973 µm`.

```
olculen baseline periyodu  = 17.96 nm   (araliklar 17.2, 18.1, 18.1, 17.5, 18.9)
```

## Kaynağın kimliği: halka değil, facet'ler

| kavite | tahmini periyot |
|---|---|
| bus facet-facet, tur yolu `2L = 32 µm`, `n_g ~ 4.2` | **17.66 nm** |
| halka, çevre `~30 µm`, `n_g ~ 4.2` | 18.84 nm |
| **ölçülen halka FSR** (rezonans konumlarından) | **18.93 nm** |
| **ölçülen baseline periyodu** | **17.96 nm** |

Baseline periyodu facet tahminine uyuyor, halka FSR'sinden `%5` farklı. Kesin
ayrım, iki tarağın birbirinden **yürümesi**: baseline maksimumlarının halka
rezonanslarına göre offseti bant boyunca tek-düze kayıyor —
`+3.74, +2.44, +1.97, +1.04, -1.07 nm`. Ortak bir kavitede bu olmaz.

İki ek kanıt:

- Halka rezonansları maskeli olduğu halde `%40` salınım kalıyor. Halkanın
  `0.159 nm` FWHM'li dar çizgileri 18 nm'lik geniş bir sinüs üretemez.
- Fringe kontrastı `(max-min)/(max+min) = 0.27` → facet başına `~%14` etkin
  genlik yansıması. `n_eff = 2.4` mod ile oksit `n = 1.44` arasındaki Fresnel
  yansıması `%6` güç (`r = 0.25` genlik); mod uyumsuzluğu düşürür. Aynı mertebe.

## Kök neden

Bus `x = -8 … +8` arasında çiziliyor (`bus_length_um = 16`), domain ise `±9`
(`+ 2 x domain_padding_um`). Kılavuz **domain'in içinde bitiyor** ve arkasında
PML'e kadar 1 µm oksit var. İki kesilmiş uç yüz bir Fabry-Pérot kavitesi kuruyor;
`mode:bus_through:in` bu kavitenin içine enjekte ediyor,
`flux:bus_through:out` içinden ölçüyor.

**Bugüne kadarki her ölçüm bu `±%20` dalgalanmanın üstünde alındı.** Mutlak
`T_through` / `T_drop` değerleri, dolayısıyla `Q_i`/`Q_e` ayrımı bundan
etkilenmiştir. Drop tepesi ile through çukuru arasındaki `46 pm` kayma da
(freq-rung-1 §4c) FP kaynaklı Fano girişimiyle açıklanabilir — o ayrı
doğrulama ister.

Ne etkilenmez: **çizgi genişliği**. `Q_loaded ~ 9 650`, iki portta bağımsız
olarak aynı çıktı ve genlik kalibrasyonundan bağımsız bir ölçümdür. FP zarfı
18 nm ölçeğinde, rezonans çizgisi `0.16 nm` ölçeğinde; karışmazlar.

## Düzeltme: `bus_overhang_um` (schema `/2`)

Bus artık her port düzleminden `bus_overhang_um` kadar daha uzun çiziliyor, böylece
uç yüzler domain'i terk edip PML içinde sonlanıyor. Kavite ortadan kalkar.

Provenance korumaları:

- `domain_size_um` **kasten** `bus_length_um`'e bağlı kalıyor, çizilen uzunluğa
  değil. Overhang domain'i büyütmez, dolayısıyla hücre sayısı ve maliyet aynı
  kalır (`18.0 µm` doğrulandı).
- `_port_plane` de `bus_length_um/2`'den türediği için port düzlemleri `±8`'de
  sabit kalıyor.
- `bus_overhang_um = 0` iken alan kanonik sözlükten **çıkarılıyor** ve şema `/1`
  olarak beyan ediliyor. Böylece kilitli lineer merdivenin geometry hash'i
  `6844d49cf1585fc4df1c23ad8e60c2a9771f4a13d1df97e6408099ca0187147e`
  birebir korunuyor — sekiz manifest de geçerli kalıyor.
- Doğrulama: `bus_overhang_um <= domain_padding_um` fail-closed reddediliyor,
  çünkü padding'i geçmeyen bir overhang facet'i domain içinde bırakır.

Kanıt: `tests/fdtd/test_bus_overhang.py` (19 test), kilitli hash literal olarak
pinlendi — bu regresyon koruması daha önce hiç yoktu. Depo: `204/204` FDTD +
`82/82` benchmark = `286/286 OK`.
