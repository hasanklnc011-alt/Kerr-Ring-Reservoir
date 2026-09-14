# Plan 2 Kerr çalışma alanı

Kanonik sözleşme: [Plan 2 ADR](../../docs/decisions/2026-09-14-plan2-kerr-reservoir.md).
Sahip Claude (kod/test); Codex dokümantasyon.

## Durum

| aşama | konu | durum |
|---|---|---|
| G0 | kör-test güvenliği | **CLOSED** |
| G2 | Kerr bellek üçgeni | **CLOSED** |
| G1 | mode solver sağlığı | **CLOSED (PASS)** |
| SLOT | slot/port bütçesi | **KİLİTLİ** — 8 slot × 4 port = 32 özellik |
| P0 | çalışma alanı, protokol, kayıt biçimi | **CLOSED** |
| P1 | malzeme ve güç fizibilitesi | OPEN |
| P2–P6 | — | OPEN |

Hiçbir fiziksel kapı geçilmedi; hiçbir ücretli solve yapılmadı.

## Belgeler

- [BENCHMARK-PROTOCOL.md](BENCHMARK-PROTOCOL.md) — görev, readout, kontroller, kapılar, kayıt biçimi
- [PLATFORM-EVIDENCE.md](PLATFORM-EVIDENCE.md) — malzeme kanıt tablosunun biçimi (P1 açık)
- [MEMORY-TRIANGLE.md](MEMORY-TRIANGLE.md) — G2: `Q_floor` türetimi ve platform taraması
- [SLOT-DECISION.md](SLOT-DECISION.md) — slot/port bütçesi ve ESN referans eğrisi
- [G1-MODE-DIAGNOSTIC.md](G1-MODE-DIAGNOSTIC.md) — mode solver kök nedeni ve kapı

## Kilitli readout

Tek doğru kaynak `plan2_kerr/readout_contract.py`:
**8 mask slotu × 4 fiziksel port = 32 özellik**, slot sonu örnekleme,
dijital tap yok, ridge yalnız train iç ayrımından.

Fiziksel sonucu: `T_sym = 160 ps`, `Q_floor = 1.94e6`, `Q_i ≥ 3.89e6`,
kayıp `≤ 0.091 dB/cm` (`n_g = 2.0`, kritik kuplaj).

## Deney kayıtları

`experiments/` altında, kimlik `plan2-kerr-P<n>-<####>`, şema
`plan2-kerr-experiment/1`. Append-only; hash'ler yeniden hesaplanır.

```bash
python -m plan2_kerr.provenance verify
python -m plan2_kerr.provenance show plan2-kerr-P0-0001
python -m plan2_kerr.provenance next-id --phase 1
```

## Kurallar

Ortak benchmark ve kör suite kopyalanmaz. İki hat arasında yalnız tek nihai
kör aday. Ham büyük veri Git dışında; konum ve hash kayıtlı. Boş dosya kabul
kanıtı olmaz.

## Araştırma hattı bağlantıları

- [[docs/PROJECT-CHARTER|Üst proje]]
- [[docs/decisions/2026-09-14-plan2-kerr-reservoir|Plan 2 karar ve kapıları]]
