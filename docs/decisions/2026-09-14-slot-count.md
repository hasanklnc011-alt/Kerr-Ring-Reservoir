# Slot sayısı düşürülüyor; port sayısı açık karar

- Durum: **slot azaltma KABUL EDİLDİ** (Hasan, 2026-09-14).
  Nihai `(slot, port)` çifti **AÇIK** — port sayısı Plan 2 ADR'sini değiştirir.
- Sahip: Claude (kod/test); karar Hasan.
- Rapor: [studies/plan2-kerr/SLOT-DECISION.md](../../studies/plan2-kerr/SLOT-DECISION.md)
- Üst kararlar: [G2](2026-09-14-g2-memory-triangle.md), [Plan 2 ADR](2026-09-14-plan2-kerr-reservoir.md)

## Karar

G2'nin üç kaldıracından **slot sayısını düşürmek** seçildi. Bant genişliğini
zorlamak ve `ε`'u gevşetmek bu turda uygulanmıyor.

## Kaldıracın tek başına yetmediği

`özellik = slot × port`. Slotu kesmek `Q_floor`'u düşürürken readout
bütçesini de düşürüyor. Kritik asimetri: **`Q_floor` yalnız slot sayısına
bağlı, port sayısı formülde geçmiyor.** Sabit özellik hedefinde slot kalite
faktörüne mal oluyor, port olmuyor.

Dolayısıyla kararın uygulanabilir hâli: **slot ↓ + port ↑**.

## Özellik hedefi

ESN referansından değil, bu projenin kendi sonuçlarından:

| kaynak | özellik | medyan NMSE |
|---|---|---|
| P2 spiral, ideal model | 20 | 0.039716 |
| P3, nominal fizik profili | **30** | 0.038246 |
| P5 kör | 30 | 0.038705 |

20 özellik ideal modelde yetmiş, gerçekçi fizikte elenmiş. **Çalışma hedefi
30 özellik.**

## ESN referansı — düzeltme kaydı

Dev seed'lerde ayarlanmış bir leaky-ESN geliştirme kapısını ilk **300
özellikte** geçiyor (20 özellikte medyan 0.486).

Bu eğriyi ilk yazdığımda "özellik alt sınırı" diye çerçevelemiştim; **yanlıştı
ve düzeltildi**. ESN jenerik rastgele bir açılımdır; P2'nin 20 özellikle
0.0397 alması doğrudan karşı kanıttır. Eğri artık *referans* olarak
etiketlendi ve şunu kalibre ediyor: 30 özellikle bu işi yapmak, açılımın
rastgeleden yaklaşık **×10 daha verimli** olması demek.

## Öneri (onaya tabi)

**8 slot × 4 port = 32 özellik.**

| | nominal Plan 2 | öneri |
|---|---|---|
| slot × port | 20 × 2 | 8 × 4 |
| özellik | 40 | 32 |
| `T_sym` | 400 ps | 160 ps |
| `Q_floor` | 4.86e6 | **1.94e6** |
| `Q_i` gerekli | 9.72e6 | **3.89e6** |
| maks kayıp (`n_g=2.0`) | 0.036 dB/cm | **0.091 dB/cm** |

`Q_i` talebi 2.5 kat düşüyor ve kaynaklı AlGaAsOI cihazının (`3.52e6`)
mertebesine iniyor; iyi SiN'in rahat aralığında.

## Portun bedeli

`Q_floor`'da geçmiyor ama fizikte geçiyor: her port bir detektör; bir-iki
halkalı bir cihazda **bağımsız** optik port sayısı sınırlı (through/drop ve
karşılıkları). Spiral hattının 10 PD'si uzun bir spirali on noktadan
tapleyerek elde edilmişti, kompakt halka çifti bunu sunmaz.

Plan 2 ADR'si §4 **2 port / 40 özellik** olarak sabitlemiş ve "eşit
detector/özellik bütçesi" kuralı koymuştur. Port sayısını 4'e çıkarmak bu
sözleşmeyi değiştirir; bu yüzden burada **önerilmiştir, uygulanmamıştır**.

## Açık

- Hasan: port sayısı 2'de mi kalsın, 4'e mi çıksın? 2'de kalırsa özellik
  hedefi için `15 slot × 2 port = 30 özellik` gerekir ve `Q_i ≥ 7.29e6`
  (0.048 dB/cm) demektir — ulaşılabilir ama zorlu.
- Portların **bağımsızlığı** P2'de kontrol edilecek: aynı rezonansın iki
  yüzünü iki port saymak özellik değil gürültü üretir.
- `ε = 1/e` hâlâ modelleme seçimi (G2'nin açık zayıf halkası).
- 32 özelliğin Kerr halkasında yeteceği **gösterilmedi**; gösterilen, bu
  projede 30 özelliğin *başka bir mimaride* yetmiş olmasıdır.

## Kanıt

`plan2_kerr/slot_decision.py`, `plan2_kerr/feature_floor.py`;
`tests/plan2_kerr/` 61/61. Dev seed'ler kullanıldı, kör suite'e dokunulmadı,
ücretli solve yok.
