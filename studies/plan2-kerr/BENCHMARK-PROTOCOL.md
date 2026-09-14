# Plan 2 benchmark protokolü

Kanonik sözleşme: [Plan 2 ADR](../../docs/decisions/2026-09-14-plan2-kerr-reservoir.md) §2.
Readout kararı: [slot/port](../../docs/decisions/2026-09-14-slot-count.md).
Bu dosya ortak benchmarkı **yeniden tanımlamaz**, ona referans verir.

## 1. Görev ve veri — ortak, değişmez

`benchmarks/narma10_np/` bu hatta **kopyalanmaz**, doğrudan kullanılır.

| | |
|---|---|
| Görev | NARMA-10 (`α=0.3, β=0.05, γ=1.5, δ=0.1`) |
| Giriş | `u[t] ~ U[0, 0.5]`, i.i.d. |
| Bölme | 200 washout + 3000 train + 2000 test |
| Geliştirme | 5 seed, `narma10/dev`, master `20260910` |
| Kör | 10 seed, `narma10/blind`, master `909314159265358` |
| Hash'ler | `manifests/narma10/{dev,blind}_seeds.sha256.json` |

Sabitler `benchmarks/narma10_np/config.py`'de; değiştirmek karar kaydı ister.

## 2. Readout sözleşmesi — Plan 2'ye özel

Tek doğru kaynak: `plan2_kerr/readout_contract.py`.

| | değer |
|---|---|
| Sembol başına mask slotu | **8** |
| Fiziksel çıkış portu | **4** |
| Özellik sayısı | **32** |
| Örnekleme | slot sonu (`slot_end`) |
| Semboller arası dijital tap | **0** |
| Ridge seçimi | yalnız train iç ayrımı |

Bu, Plan 2 ADR §4'ün `20 × 2 = 40` sayısını değiştirir; gerekçe slot/port
karar kaydındadır. Maske dizisi ve seed'i ilk skordan **önce** kilitlenir ve
tüm mimarilerde aynıdır.

Fiziksel sonuçları (`m=10`, `B=50 GHz`, `ε=1/e`, `n_g=2.0`, kritik kuplaj):
`T_sym = 160 ps`, `Q_floor = 1.94e6`, `Q_i ≥ 3.89e6`, kayıp `≤ 0.091 dB/cm`.

## 3. Kontroller

Her aday için ayrı ayrı raporlanır:

- input-only (reservoir yok),
- belleksiz PD,
- aynı lineer optik yapı + PD,
- Kerr kapalı,
- tam model,
- dijital baseline, 0/1/5/10/20 geçmiş örnekle.

Ablation tek başına üstünlük değildir: yeniden optimize edilmiş lineer kontrol
ayrıca raporlanır. Başlangıç duyarlılığı ve fading memory ölçülür.

## 4. Kapılar

| aşama | kapı |
|---|---|
| P3 geliştirme | 5 seed medyan `< 0.04` **ve** ≥4/5 seed `< 0.05` |
| P3 Kerr katkısı | aynı çalışma noktasında Kerr-off medyanına göre ≥ %10 göreli iyileşme |
| P3 sayısal | zaman çözümü sıkılaşınca NMSE değişimi `< %1` |
| P5 dayanıklılık | 64 ön kayıtlı senaryonun ≥ %90'ında beş-seed medyan `< 0.05` |
| Nihai kör | medyan `< 0.05` **ve** ≥8/10 seed `< 0.05` |

## 5. Kör suite

Bu depoda tek kopya, tek kullanım. Yol: guard (salt-okunur) → süreç kilidi →
skordan **önce** atomik rezervasyon → kilitli scorer → kayıt. Ayrıntı ve
kurtarma kuralları: [G0 karar kaydı](../../docs/decisions/2026-09-14-g0-blind-test-safety.md).

Kör sonuçtan sonra tuning yoktur. Farklı aday kimliği suite'i yeniden açamaz.
Plan 2, Plan 1 ve kurtarma hattı aynı suite'i paylaşır; **tek nihai aday**.

## 6. Deney kaydı

Her sonuç `plan2-kerr-P<n>-<####>` kimliğiyle
`studies/plan2-kerr/experiments/` altına yazılır. Şema
`plan2-kerr-experiment/1`, üretici `plan2_kerr/provenance.py`.

Kayıt append-only'dir; hash'ler `verify` ile yeniden hesaplanır; kaynaksız
parametreler `unresolved` olarak görünür kalır.

```bash
python -m plan2_kerr.provenance env
python -m plan2_kerr.provenance next-id --phase 1
python -m plan2_kerr.provenance verify
```

## 7. Bu protokolün kapsamadığı

Fiziksel model (P2), malzeme tablosu (P1), geometri (P4) ve EM doğrulaması
(P6) burada tanımlanmaz. Bu dosya yalnız görevi, readout'u, kontrolleri,
kapıları ve kayıt biçimini sabitler.
