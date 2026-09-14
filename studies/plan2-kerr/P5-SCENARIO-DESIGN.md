# P5 senaryo tasarımı — TASLAK

Durum: **TASLAK.** İlk P5 skorundan önce dondurulacak (Plan 2 ADR §7:
"64 ön kayıtlı senaryo"). Eksenlerin yapısı burada; malzeme aralıkları P1'i
bekliyor.

Üretim: `./.venv-mode-211/Scripts/python.exe -m fdtd.modes sensitivity` ve `... coupling`
Ham veri: `reports/tolerance/geometry-sensitivity.json`, `reports/tolerance/gap-coupling.json`
Kayıtlar: `plan2-kerr-P5-0002` (geometri), `plan2-kerr-P5-0003` (gap)

## 0. Neden şimdi

P5 kapısı "64 senaryonun ≥%90'ında beş-seed medyan `< 0.05`" diyor, ama
senaryoların **nereye** konacağı ölçülmüş hassasiyet olmadan keyfî olurdu.
Geometri → rezonans hassasiyeti artık G1'de doğrulanmış solver'la ölçüldü,
dolayısıyla eksenler sayıya oturtulabiliyor.

Bu bir P5 **girdisidir**, P5 sonucu değildir. Hiçbir kapı geçmez.

## 1. Ölçülen geometri hassasiyeti

Merkezî fark, ±1 nm, 26 step/λ, local subpixel açık.

| kesit | `dn_eff/dw` | `dn_eff/dh` | `dλ/dw` | `dλ/dh` |
|---|---|---|---|---|
| Si 450×220 | 2.393 /µm | 5.214 /µm | **894.2 pm/nm** | 1948.1 pm/nm |
| SiN 1200×800 | 0.1254 /µm | 0.2576 /µm | **92.8 pm/nm** | 190.7 pm/nm |

Linewidth cinsinden (`FWHM = λ/Q_L`):

| | linewidth | Si genişlik | Si kalınlık | SiN genişlik | SiN kalınlık |
|---|---|---|---|---|---|
| çalışma `Q_L = 4.22e5` | 3.67 pm | 243.6 /nm | 530.7 /nm | **25.3 /nm** | 51.9 /nm |
| katı `Q_L = 1.94e6` | 0.80 pm | 1121.7 /nm | 2443.9 /nm | 116.4 /nm | 239.2 /nm |

### Üç okuma

1. **`ε` gevşemesi toleransa yardım ediyor.** Düşük `Q` → 4.6 kat geniş
   linewidth → 4.6 kat fazla tolerans payı. Retention kararı bu açıdan
   yanıltıcı değil, lehte.
2. **Buna rağmen trim kaçınılmaz.** Gevşemiş `Q`'da bile 1 nm genişlik hatası
   SiN'de rezonansı 25 linewidth kaydırıyor. Proses toleransı birkaç nm ise
   rezonans yüzlerce linewidth uzağa düşer. Aktif trim mimarinin parçasıdır,
   opsiyon değil.
3. **Kalınlık genişlikten baskın** (SiN'de 2.1×, Si'de 2.2×). Film kalınlığı
   tipik olarak dilim içinde genişlikten daha iyi kontrol edilir ama dilimler
   arası kayar; bu ayrı bir eksen olmalı.

**SiN, Si'den ~9.6 kat daha az hassas.** G1 platform değişiminin *sayısal*
gerekçesini çürütmüştü; bu *fiziksel* bir gerekçe ve ayakta duruyor.

## 2. Senaryo eksenleri

Hedef 64 senaryo = 6 ikili eksen, ya da ağırlıklı bir tasarım. Taslak:

| # | eksen | durum | not |
|---|---|---|---|
| 1 | kılavuz genişliği | **ölçüldü** (hassasiyet) | aralık P1'den (proses toleransı) |
| 2 | film kalınlığı | **ölçüldü** (hassasiyet) | ortak mod: iki halka birlikte kayar |
| 3 | bus–ring ve ring–ring gap | **ölçüldü** | `κ` üstel; SiN 0.54 %/nm, Si 0.85 %/nm |
| 4 | halkalar arası rezonans uyumsuzluğu | kısmen | eksen 1–2'den türer; **yerel** varyasyon gerekir |
| 5 | lineer kayıp | AÇIK | P1 |
| 6 | Kerr katsayısı | AÇIK | P1 |
| 7 | lazer detuning | AÇIK | trim çözünürlüğüne bağlı |
| 8 | giriş gücü | AÇIK | P1 güç bütçesi |

**Ortak proses sapması ile halka başına farklılık ayrılacaktır** (ADR §7).
Aynı dilimdeki iki halka genişlik hatasının büyük kısmını *paylaşır*; onları
ayıran şey yerel varyasyondur ve reservoir'ın istediği rezonans ilişkisini
bozan da odur. İkisini tek eksen saymak senaryo kapsamını şişirir.

## 2b. Ölçülen gap → `κ` hassasiyeti

İki özdeş kılavuz, **parity ile seçilmiş** çift/tek supermode,
`κ = π·Δn/λ` (genlik kuplajı, 1/m). Parity her gap'te temiz: `+1.00 / −1.00`.

| gap (nm) | Si `κ` (1/m) | Si `L_c` (µm) | SiN `κ` (1/m) | SiN `L_c` (µm) |
|---|---|---|---|---|
| 150 | 96600 | 16.3 | 49944 | 31.5 |
| 200 | 62210 | 25.3 | 37384 | 42.0 |
| 250 | 40586 | 38.7 | 28433 | 55.3 |
| 300 | 26689 | 58.9 | 22912 | 68.6 |

Üstel uyum `κ = κ₀·exp(−g/L_d)`:

| kesit | `L_d` | `R²` | `\|d ln κ / dg\|` |
|---|---|---|---|
| Si 450×220 | 117.7 nm | 0.99932 | **0.85 %/nm** |
| SiN 1200×800 | 185.5 nm | 0.98967 | **0.54 %/nm** |

### Bu, eski hattın yanlış aldığı ölçüm

Eski depo `κ`'yı 150→300 nm boyunca **altı hanede sabit** raporlamıştı;
seçici parity yerine en yüksek iki `n_eff`'i alıyordu. Burada `κ` 150→300 nm
arasında Si'de 3.6, SiN'de 2.2 kat düşüyor. Sweep, monoton düşmeyen bir `κ`'yı
yapısal olarak reddediyor.

### Tolerans sonucu — gap baskın risk değil

±10 nm gap hatası `κ`'yı SiN'de %5.4, Si'de %8.5 değiştiriyor; `Q_e ∝ 1/κ²`
olduğundan `Q_e`'de ~%11–18. Karşılaştırın: **1 nm genişlik hatası SiN'de
25 linewidth rezonans kayması.** Yani üretim riskinin baskın ekseni
**rezonans hizalaması**, kuplaj değil. P5 senaryo ağırlıkları buna göre
kurulmalı.

**Uyarı:** bu düz kılavuz `κ`'sıdır. Gerçek halka–bus kuplörü boyunca gap
değişir ve `κ(s)` integre edilmelidir; bu P4 işidir.

## 3. Trim bütçesi — hesaplanamıyor

`trim_range_nm()` hazır ama **termo-optik ayar verimliliği (`pm/K`)
`unresolved`**, bu yüzden `None` döndürüyor. P1 bunu kaynaklayana kadar
ısıtıcı gücü ve trim aralığı hesaplanamaz.

Uyarı: termal trim, kullanmayı planladığımız termal dinamiğin *aynı* kanalını
kullanıyor. Statik trim ile çalışma noktasının termal kayması birbirine
karışır; eski spiral hattı bu yüzden thermal'ı statik role kilitlemişti.
Bu P2'nin model ayrımı sorunudur.

## 4. Dondurma koşulu

Gap → `κ` hassasiyeti artık ölçüldü. Kalan iki koşul: **P1 malzeme/proses
aralıkları** ve **P2/P3'ten çalışma noktası**. Dondurulduğunda 64 senaryo
hash'lenip ilk skordan önce kayda geçecek.

## 5. Sınırlar

Düz kılavuz kesiti; bend ve gerçek halka–bus kuplör geometrisi dahil değil. Tek dalga
boyu (1550 nm), tek mod. Sıcaklık, gerilim ve yaşlanma kaymaları yok. Malzeme
indisleri standart çalışma figürleri, kaynaklı değil (P1).
