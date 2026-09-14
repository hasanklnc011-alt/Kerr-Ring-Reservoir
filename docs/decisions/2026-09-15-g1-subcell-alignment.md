# G1 düzeltmesi — hücre-altı hizalama ekseni ve ofset ortalaması

- Durum: **KABUL EDİLDİ**, 2026-09-15. [G1 kararını](2026-09-14-g1-mode-solver.md) düzeltir.
- Sahip: Claude (kod/test).
- Rapor: [studies/plan2-kerr/G1-ALIGNMENT.md](../../studies/plan2-kerr/G1-ALIGNMENT.md)
- Ham veri: `reports/g1/alignment-study.json`

## Neyi düzeltiyor

2026-09-14 tarihli G1 kararı "dört kapı da geçti, mode solver kabul edilir"
diyordu. Bu **fazla genişti**. Dört kapı — öteleme, mesh, grup indisi,
örtüşme — hepsi **tek bir grid hizalamasında** ölçülmüştü. Hizalama ekseni
hiç test edilmemişti.

## Bulgu

Sabit domain, sabit grid, local subpixel **açık**. Yapı hücre-altı ötelendiğinde:

| öteleme | `n_eff` | Δ |
|---|---|---|
| 0 | 2.353928871 | 0 |
| dl/4 | 2.358595800 | +4.67e-03 |
| dl/2 | 2.368097852 | **+1.42e-02** |
| 3dl/4 | 2.358522191 | +4.59e-03 |
| dl | 2.353928419 | −4.5e-07 |

Tam bir hücrede başa dönüyor (4.5e-7). Çekirdek hapsi 0.591–0.600 arasında
sabit, yani aynı fiziksel mod; seçici sorunu değil. **Bu bir grid-kayıt
etkisidir.**

`1e-12 µm` testinin tam sıfır vermesiyle çelişmiyor: subpixel ortalaması
süreksizliği kaldırıyor, sonlu hücre-altı bağımlılığı kaldırmıyor.

## Mesh inceltmek çözüm değil

| spw | dl (nm) | salınım | ofset ortalaması |
|---|---|---|---|
| 16 | 27.84 | 2.2605e-02 | 2.361706285 |
| 20 | 22.27 | 1.7850e-02 | 2.360669532 |
| 26 | 17.13 | 1.4169e-02 | 2.359786178 |
| 32 | 13.92 | 1.2268e-02 | 2.359656154 |
| 40 | 11.14 | 1.2086e-02 | 2.359156604 |

`dl` 2.5 kat inerken salınım yalnız **1.87 kat** düşüyor ve duruyor: görünür
yakınsama mertebesi 1.06 → 0.88 → 0.69 → **0.07**. Son inceltme (32→40)
sadece 1.8e-4 kazandırıyor. **Tek hizalamalı `n_eff`, mesh ne kadar ince
olursa olsun 1e-2 düzeyinde belirsizdir.**

## Karar: üretim değeri ofset ortalamasıdır

Ofset ortalaması son iki mesh arasında **5.0e-4** oynuyor — `1e-3` yakınsama
kapısının içinde.

Bundan sonra:

1. Üretim girdisi olacak her `n_eff`/`n_g`, dört hücre-altı ofsetin
   (`0, dl/4, dl/2, 3dl/4`) **ortalamasıdır**.
2. Alıntılanan belirsizlik **salınımdır**, mesh-mesh farkı değil.
   Nominal noktada bu `±6e-3` (yarı salınım) mertebesindedir.
3. Tek ofsetli bir sayı **tanıdır, girdi değildir.**

Uygulama: `fdtd/modes/alignment.py`, `sensitivity.measure(offset_averaged=True)`
artık varsayılan.

## Neden merdiven temiz görünmüştü

Çekirdek duvarı ±0.225 µm'de. Merdivendeki dört mesh için `0.225/dl` =
8.082, 10.103, 13.134, 16.164 — kesir kısımları hepsi 0.08–0.16. Duvar dört
koşuda da neredeyse **aynı** hücre-altı konumda oturmuş. Merdivenin `6.8e-4`'e
yakınsamış görünmesi yakınsamadan çok hizalamanın korele olmasındandı.

## Etkilenen sonuçlar

| sonuç | durum |
|---|---|
| G1 "dört kapı PASS" | **daraltıldı**: tek hizalamada geçerli; ofset ortalamasıyla yeniden ifade edilmeli |
| Geometri hassasiyeti (`dλ/dw`) | **yeniden ölçüldü** ofset ortalamasıyla; `geometry-sensitivity-averaged.json` |
| `κ(gap)` | tek hizalamada ölçüldü; **nitel sonuç (üstel düşüş, parity) sağlam**, mutlak `L_d` yeniden ölçülmeli |
| G0, G2, `ε`, slot/port | **etkilenmedi** — hiçbiri `n_eff`'in mutlak değerine bağlı değil |

## Eski hükümlerin son hâli

- "Tüm yerel mode solver kullanılamaz" — hâlâ **yanlış**. Solver kullanılabilir.
- "Kök neden eksik subpixel ortalaması" — **eksik**. Subpixel hatayı süreklileştirip
  küçültüyor ama bitirmiyor; kalan mekanizma hücre-altı hizalama bağımlılığıdır.
- `GridSpec.auto`'nun grid-çizgisi yaslaması bu bağımlılığın **yükselteci**;
  hâlâ üretimde kullanılmamalı.

## Sınırlar

Tek kesit (Si 450×220), tek eksende (z) öteleme, dört ofset. x eksenindeki
hizalama ayrıca sınanmadı; muhtemelen benzer davranır ama ölçülmedi.
Uzak (cloud) çözücüyle karşılaştırma yapılmadı.
