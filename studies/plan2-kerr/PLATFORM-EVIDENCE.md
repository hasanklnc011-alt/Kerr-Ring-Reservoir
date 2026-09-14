# Platform kanıt tablosu

Durum: **P1 AÇIK.** Bu dosya şu an *biçimi* sabitliyor, içeriği değil.
Kanonik sözleşme: [Plan 2 ADR](../../docs/decisions/2026-09-14-plan2-kerr-reservoir.md) §3.

## Statü tanımları (`const.md`)

| statü | anlamı |
|---|---|
| `source-supported` | fiilen okunmuş birincil kaynak; birim, dalga boyu, sıcaklık, proses/geometri bağlamı kayıtlı |
| `EM-supported` | bu geometrinin EM ölçümünden, yakınsama kanıtıyla |
| `synthetic` | yalnız sentetik/analitik testte kullanılabilir |
| `unresolved` | eksik; sessiz varsayılanla doldurulmaz, NMSE'ye uydurulmaz |

Statü etiketi tek başına kabul değildir; ilgili kapı kanıtı gerekir.

## Zorunlu satırlar

Her aday platform için, **tek bir proses/geometri bağlamı paylaşarak**:

`n` (lineer indis), `n_g`, dispersiyon, `n2`, `A_eff`, lineer kayıp,
`beta_TPA`, `sigma_FCA`, `dn/dN`, `dn/dT`, `tau_FC`, `tau_th`, ısıl kapasite,
termal direnç, minimum özellik boyutu, eğrilik sınırı.

Her satır: birim, birincil kaynak (denklem/sayfa), artefakt hash'i, dalga
boyu, sıcaklık, proses/geometri uyumu, nominal + aralık, dönüşüm, kabul durumu.

**Farklı cihazların en iyi özellikleri tek hayalî cihazda birleştirilmez.**

## Si3N4 / SiO2

| büyüklük | değer | birim | statü | kaynak |
|---|---|---|---|---|
| hepsi | — | — | `unresolved` | P1 açık |

## AlGaAs-on-insulator

| büyüklük | değer | birim | statü | kaynak |
|---|---|---|---|---|
| `Q_i` (gösterilmiş cihaz) | 3.52e6 | 1 | `source-supported` | Xie ve ark., Opt. Express 28(22), 32894 (2020), arXiv:2004.14537 — özet 2026-09-14'te okundu; finesse 1.4e4 |
| diğer hepsi | — | — | `unresolved` | P1 açık |

## Karşılanması gereken eşik

Readout kararından sonra: `Q_i ≥ 3.89e6`, yani `n_g = 2.0` için kayıp
`≤ 0.091 dB/cm`. Kaynaklı AlGaAsOI cihazı (`3.52e6`) bu eşiğin hemen altında;
SiN tarafı için kaynaklı bir kayıp figürü henüz yok.

## Kapı

P1, kaynak kapsamı yeterli olan platformlarda eşit P3 taraması yapılmasına
izin verir. Nihai platform seçimi **P3 sonrasında** kapanır; kaynak incelemesi
ile platform seçimi birbirine karıştırılmaz. Hiçbiri fizibilite göstermezse
üçüncü platforma otomatik geçilmez.
