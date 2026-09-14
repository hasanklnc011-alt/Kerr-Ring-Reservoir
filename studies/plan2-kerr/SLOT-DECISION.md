# Slot sayısı kararı — iki taban birlikte

Üretim komutları:

```bash
python -m plan2_kerr.slot_decision
python -c "from plan2_kerr.feature_floor import ESNSpec, sweep; ..."   # ESN referans eğrisi
```

Kod: `plan2_kerr/slot_decision.py`, `plan2_kerr/feature_floor.py`
Testler: `python -m tests.plan2_kerr.run_tests` (61/61)
Karar kaydı: [2026-09-14-slot-count](../../docs/decisions/2026-09-14-slot-count.md)

## 0. Özet

Hasan'ın kararı: **slot sayısını düşür.** Fizik tarafında doğru kaldıraç.
Ama tek başına uygulanırsa readout bütçesini de düşürüyor, çünkü
`özellik = slot × port`.

Kritik asimetri şu: `Q_floor` **yalnız slot sayısına** bağlı, port sayısı
formülde hiç geçmiyor.

```
Q_floor = m · ω₀ · N / ( ln(1/ε) · B )
```

Yani sabit bir özellik hedefinde **slot kalite faktörüne mal oluyor, port
olmuyor.** Slotu kesip özelliği porttan geri almak, bellek kısıtını readout'u
daraltmadan gevşeten tek hamle.

## 1. Özellik hedefi nereden geliyor

ESN referans eğrisinden **değil**. Kendi geçmişimizden:

| kaynak | özellik | medyan NMSE | not |
|---|---|---|---|
| P2 (spiral hattı) | **20** | 0.039716 | ideal koherent model, 8/10 kör seed |
| P3 (10 PD × 3 slot) | **30** | 0.038246 | nominal fizik profili, 9/10; burada 20-özellikli aday elendi |
| P5 kör | 30 | 0.038705 | kilitli aday, tek kör değerlendirme, 8/10 |

**Çalışma hedefi 30 özellik.** 20 özellik ideal modelde yetmiş ama gerçekçi
fizik profilinde elenmiş; bu yüzden 30 alınıyor.

## 2. ESN referans eğrisi — ve neden taban değil

Dev seed'lerde, aynı split ve aynı ridge ile, ayarlanmış bir leaky-ESN:

| özellik | 20 | 30 | 40 | 60 | 100 | 150 | 200 | 250 | 300 | 400 |
|---|---|---|---|---|---|---|---|---|---|---|
| medyan NMSE | 0.486 | 0.234 | 0.183 | 0.150 | 0.077 | 0.050 | 0.045 | 0.042 | **0.029** | 0.022 |

Geliştirme kapısını (medyan < 0.04 **ve** ≥4/5 seed < 0.05) ilk geçen nokta
**300 özellik**.

İlk yazdığımda bu eğriyi "özellik alt sınırı" diye çerçevelemiştim. **Yanlıştı
ve düzelttim.** ESN *jenerik rastgele* bir açılım; ısmarlama bir mimari aynı
özellik sayısında çok daha verimli olabiliyor. Kendi P2 sonucumuz bunun
kanıtı: 20 özellikle 0.0397. ESN aynı işi ~300 özellikle yapıyor.

Eğrinin gerçek faydası şu: **bir mimarinin ne kadar özellik-verimli olması
gerektiğini kalibre ediyor.** 30 özellikle 300-özellikli ESN'i yakalamak,
açılımın rastgeleden yaklaşık **bir kat (×10) daha iyi** olması demek.
Spiral hattı bunu başarmıştı; Kerr halkasının da başarması gerekiyor ve bu
bedava değil.

ESN hiperparametreleri dev seed'lerde tarandı (spectral_radius ∈ {0.7,0.9,1.1,1.3},
leak ∈ {0.2,0.5,1.0}, input_scale ∈ {0.2,0.5,1.0}, 40 özellikte); seçilen
`sr=0.9, leak=1.0, input=0.2`. Kör suite'e dokunulmadı.

## 3. Ortak tablo

`m=10`, `B=50 GHz`, `ε=1/e`, `n_g=2.0`, kritik kuplaj.

| slot | port | özellik | `T_sym` | `Q_floor` | `Q_i` gerekli | maks kayıp |
|---|---|---|---|---|---|---|
| 20 | 2 | 40 | 400 ps | 4.86e6 | 9.72e6 | 0.036 dB/cm |
| 15 | 2 | 30 | 300 ps | 3.65e6 | 7.29e6 | 0.048 dB/cm |
| 12 | 4 | 48 | 240 ps | 2.92e6 | 5.83e6 | 0.060 dB/cm |
| 10 | 4 | 40 | 200 ps | 2.43e6 | 4.86e6 | 0.072 dB/cm |
| **8** | **4** | **32** | **160 ps** | **1.94e6** | **3.89e6** | **0.091 dB/cm** |
| 5 | 6 | 30 | 100 ps | 1.22e6 | 2.43e6 | 0.145 dB/cm |
| 3 | 10 | 30 | 60 ps | 7.29e5 | 1.46e6 | 0.241 dB/cm |

Karşılaştırma için: kaynaklı AlGaAsOI cihazı `Q_i = 3.52e6`
(Xie 2020, arXiv:2004.14537).

## 4. Öneri

**8 slot × 4 port = 32 özellik.**

- `Q_i ≥ 3.89e6`, kayıp `≤ 0.091 dB/cm` — iyi SiN'in rahat aralığı, ve
  kaynaklı AlGaAsOI cihazına da çok yakın.
- 32 özellik, gerçekçi fizikle çalıştığı gösterilmiş 30 özelliğin üstünde.
- Nominal Plan 2'ye göre `Q_i` talebi **2.5 kat** düşüyor (9.72e6 → 3.89e6),
  kayıp bütçesi 2.5 kat gevşiyor.
- 4 port bir çift halka için fiziksel olarak makul: her halkanın through ve
  drop portu.

Alternatifler: daha agresif gitmek istenirse `5 slot × 6 port = 30 özellik`
kayıp bütçesini `0.145 dB/cm`'ye çıkarıyor, ama 6 bağımsız optik port iki
halkalı bir cihazda kolay değil.

## 5. Portun bedeli — bu bedava değil

`Q_floor`'da port geçmiyor, ama fizikte geçiyor:

- Her port bir **detektör** demek: alan, güç, TIA gürültüsü, kalibrasyon.
- Bir–iki halkalı bir cihazda **bağımsız** optik port sayısı sınırlı
  (through, drop ve karşılıkları). Spiral hattındaki 10 PD, uzun bir spirali
  on noktadan tapleyerek elde edilmişti; kompakt bir halka çifti bunu sunmaz.
- Plan 2 ADR'si **2 port / 40 özellik** olarak sabitlemiş ve "eşit
  detector/özellik bütçesi" kuralı koymuş. Port sayısını değiştirmek bu
  sözleşmeyi değiştirir — **Hasan'ın kararı**, benim değil.
- Portlar bağımsız olmalı: aynı rezonansın iki yüzünü iki port saymak özellik
  üretmez, gürültü üretir. Bu P2'de kontrol edilecek.

## 6. Ne kanıtlanmadı

- 32 özelliğin **Kerr halkasında** yeteceği gösterilmedi. Gösterilen: bu
  projede 30 özellik *başka bir mimaride* yetmişti. Kerr halkasının açılımı
  o kadar verimli olmayabilir.
- ESN eğrisi tek bir ESN ailesi ve tek bir ayar taraması; başka bir jenerik
  model farklı bir referans verirdi.
- `ε = 1/e` hâlâ modelleme seçimi (G2'nin açık kalan zayıf halkası).
- Malzeme sayıları `unresolved` (P1).
- Hiçbir fiziksel kapı geçilmedi; bu bir tasarım-bütçesi hesabıdır.
