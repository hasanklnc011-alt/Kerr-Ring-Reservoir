# G1 eki — hücre-altı hizalama ekseni

Üretim: `./.venv-mode-211/Scripts/python.exe scripts/alignment_study.py`
Ham veri: `reports/g1/alignment-study.json`
Karar kaydı: [2026-09-15-g1-subcell-alignment](../../docs/decisions/2026-09-15-g1-subcell-alignment.md)

## 0. Sonuç

Mode solver'ın `n_eff`'i, yapının hesap ızgarasına **hücre-altı** hizasına
bağlı. Local subpixel açıkken bile. Etki `1.4e-2` — mesh kapısının 14 katı.

**Mesh inceltmek bunu çözmüyor.** Çözüm: dört hücre-altı ofsetin ortalaması.
Ortalama `5.0e-4`'te oturuyor, yani kapının içinde.

## 1. Etki periyodik ve fiziksel değil

Sabit domain (4.45 × 4.22 µm), sabit grid (26 step/λ, dl = 17.13 nm),
yapı z'de ötelendi:

| öteleme | `n_eff` | Δ | çekirdek hapsi |
|---|---|---|---|
| 0 | 2.353928871 | 0 | 0.598 |
| dl/4 = 4.28 nm | 2.358595800 | +4.67e-03 | 0.599 |
| **dl/2 = 8.57 nm** | **2.368097852** | **+1.42e-02** | 0.600 |
| 3dl/4 = 12.85 nm | 2.358522191 | +4.59e-03 | 0.596 |
| dl = 17.13 nm | 2.353928419 | −4.5e-07 | 0.591 |

Üç gözlem:
- **Tam bir hücrede başa dönüyor** (4.5e-7). Grid-kayıt etkisinin imzası.
- **dl/2'de simetrik tepe.** dl/4 ve 3dl/4 neredeyse eşit.
- **Çekirdek hapsi sabit** (0.591–0.600) → aynı fiziksel mod, seçici sorunu değil.

`±1e-12 µm` testinin tam sıfır vermesiyle çelişmiyor. Subpixel ortalaması
süreksizliği kaldırıyor; sonlu hücre-altı bağımlılığı kaldırmıyor.

## 2. Mesh inceltmek çözmüyor

| spw | dl (nm) | salınım | ofset ortalaması | ort. farkı |
|---|---|---|---|---|
| 16 | 27.84 | 2.2605e-02 | 2.361706285 | — |
| 20 | 22.27 | 1.7850e-02 | 2.360669532 | −1.04e-03 |
| 26 | 17.13 | 1.4169e-02 | 2.359786178 | −8.83e-04 |
| 32 | 13.92 | 1.2268e-02 | 2.359656154 | −1.30e-04 |
| 40 | 11.14 | 1.2086e-02 | 2.359156604 | −5.00e-04 |

Görünür yakınsama mertebesi:

| geçiş | dl oranı | salınım oranı | mertebe |
|---|---|---|---|
| 16→20 | 1.250 | 1.266 | 1.06 |
| 20→26 | 1.300 | 1.260 | 0.88 |
| 26→32 | 1.231 | 1.155 | 0.69 |
| 32→40 | 1.250 | 1.015 | **0.07** |

`dl` 2.5 kat inerken salınım yalnız **1.87 kat** düşüyor ve `~1.2e-2`'de
**duruyor**. Son inceltme 1.8e-4 kazandırıyor. Ekstrapole edersek `1e-3` için
`dl ≈ 1 nm`, yani `spw ≈ 370` gerekir — pratik değil.

## 3. Ofset ortalaması çalışıyor

Ortalamanın son iki mesh arasındaki farkı **5.0e-4** — `1e-3` kapısının içinde.
Dört solve maliyetiyle, mesh inceltmenin başaramadığı yakınsama elde ediliyor.

**Kural:** üretim `n_eff`'i dört ofsetin ortalamasıdır; alıntılanan belirsizlik
salınımdır (nominal noktada yarı salınım ≈ `±6e-3`), mesh-mesh farkı değil.

## 4. Merdiven neden temiz görünmüştü

Çekirdek duvarı ±0.225 µm'de. Merdivendeki dört mesh için duvarın hücre-altı
konumu:

| spw | dl (nm) | 0.225/dl | kesir |
|---|---|---|---|
| 16 | 27.84 | 8.082 | 0.082 |
| 20 | 22.27 | 10.103 | 0.103 |
| 26 | 17.13 | 13.134 | 0.134 |
| 32 | 13.92 | 16.164 | 0.164 |

Dördü de **aynı bölgede** (0.08–0.16). Merdiven boyunca hizalama neredeyse
sabit kalmış; `6.8e-4`'lük "yakınsama" bunun eseri. Bu, tasarlanmış bir kontrol
değil tesadüftü — ve tesadüf olduğu için güvenilmez.

## 5. Domain taraması da bununla açıklanıyor

`pad` değiştirince domain hücre sayısı değişiyor, efektif `dl` ve duvarın
hücre-altı konumu kayıyor. Ölçülen: `pad` 1.0→5.0 µm arasında `n_eff`
**1.99e-2** yayılımla düzensizce zıplıyor (monoton değil). Aynı etki.

## 6. Etkilenen ölçümler

| ölçüm | durum |
|---|---|
| G1 dört kapı | tek hizalamada geçerli; ofset ortalamasıyla yeniden ifade edilmeli |
| `dλ/dw`, `dλ/dh` | **yeniden ölçüldü** (`geometry-sensitivity-averaged.json`) |
| `κ(gap)` | nitel sonuç sağlam; mutlak `L_d` yeniden ölçülmeli |
| G0, G2, `ε`, slot/port | etkilenmedi |

## 7. Sınırlar

Tek kesit (Si 450×220), yalnız z ekseninde öteleme, dört ofset noktası.
x eksenindeki hizalama ayrıca sınanmadı. Uzak çözücüyle karşılaştırma yok.
Dört ofsetin trapez ortalaması; daha fazla nokta daha iyi bir ortalama verebilir.
