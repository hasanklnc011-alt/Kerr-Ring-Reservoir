# 2026-09-13 — Buried-oxide sızıntı hipotezi ÇÜRÜTÜLDÜ (ücretsiz mode solver)

- Yapan: Claude Opus 5
- Maliyet: **0 FlexCredit** — Tidy3D mode solver yerel çalıştı, cloud'a gitmedi
- Script: `scratchpad/boxscan.py` (geçici; sonuçlar aşağıda kalıcı)
- Test edilen hipotez: `docs/decisions/2026-09-13-freq-rung-1-evaluation.md` §4(b)

## Hipotez

`freq-rung-1`'de rezonans dışında bile gücün `%12–23`'ü ölçülemiyordu. Malzemeler
kayıpsız olduğu için (`conductivity = 0`) bunun radyasyon/sızıntı olması
gerekiyordu, ve baş şüpheli buried oxide'ın inceliğiydi: BOX `1.0 µm`, altında
Si substrate, üstünde 450 x 220 nm Si strip. Tipik SOI 2–3 µm kullanır.

## Yöntem

Bus waveguide kesitinin modu üç BOX kalınlığıyla çözüldü. İki metodolojik
önlem alındı:

1. **Kontrol grubu**: substrate tamamen kaldırılarak aynı mod çözüldü. Orada
   sızıntı fiziksel olarak imkânsız, dolayısıyla `k_eff` gürültü tabanında
   çıkmalı. Çıkmazsa sorun fizikte değil, sayısal kurguda demektir.
2. **Mod kimliği nişan alarak değil doğrulanarak** belirlendi: `num_modes = 6`
   çözülüp çekirdekteki (`|y| <= 225 nm`, `0 <= z <= 220 nm`) güç oranı en yüksek
   mod seçildi.

### İlk denemenin hatası (kayda geçiyor)

İlk koşumda `target_neff = sqrt(eps_Si) = 3.475` verdim ve solver **Si
substrate'in slab modunu** buldu, bus modunu değil. Üç işaret bunu gösterdi:
`n_eff = 3.4687` bulk Si'ye eşitti, gücün `%96.6`'sı substrate'teydi, ve BOX
kalınlığı üç kat değişirken sonuç altıncı hanede kalıyordu. Rapor edilen
`886 dB/cm` anlamsızdı. Kesit düzlemi 2 µm Si substrate içeriyor ve o da
`n_eff ~ 3.47` civarında çok sayıda mod taşıyor.

## Sonuç

```
Si n=3.4750  SiO2 n=1.4446  lambda=1.540909 um  strip 0.45 x 0.22 um

REFERANS (substrate YOK):
  mode#0   n_eff = 2.40167   k_eff = -1.235e-08   cekirdek = 62.6%

 BOX um | mode |    n_eff |       k_eff | alpha dB/cm | cekirdek | substrate
    1.0 |    5 |  2.36693 |   4.274e-08 |        0.02 |    60.5% |     0.00%
    2.0 |    5 |  2.27958 |  -6.770e-10 |       -0.00 |    55.5% |     0.00%
    3.0 |    5 |  2.36688 |  -5.400e-10 |       -0.00 |    60.5% |     0.00%
```

**Hipotez çürütüldü.** `1.0 µm` BOX'ta sızıntı kaybı `0.02 dB/cm`, substrate'e
giden güç `%0.00`. `k_eff = 4.3e-08` referansın gürültü tabanıyla
(`-1.2e-08`) aynı mertebede, yani sıfırdan ayırt edilemiyor. Halka çevresi
~31 µm olduğundan `0.02 dB/cm` tur başına `~6e-06 dB` eder.

`n_eff = 2.4017` (referans) beklenen SOI strip değeri; kontrol grubu geçerli.

### Hüküm

**Buried oxide kalınlığı `1.0 µm` olarak KORUNUYOR.** Geometri bu açıdan
doğru; kalınlaştırma gereksiz ve `freq-rung-2` bu yüzden ertelenmemeli.

## Sonuçtaki tutarsızlık — dürüst kayıt

`BOX = 2.0 µm` satırı diğer ikisiyle uyumsuz: `n_eff = 2.2796` ve çekirdek
`%55.5`, oysa `1.0` ve `3.0` satırları `2.3669` / `%60.5` veriyor. `n_eff`'in
BOX büyüdükçe düzgün biçimde referans değere (`2.40167`) yaklaşması beklenirdi;
tek-düze olmayan bu sıçrama, `2.0 µm` satırında seçicinin biraz farklı bir mod
(muhtemelen hibrit veya farklı polarizasyon) aldığını gösterir.

Bu, hükmü değiştirmiyor: **her üç satırda da** substrate gücü `%0.00` ve
sızıntı gürültü tabanında. Ama `n_eff`'in kendisi bir kalibrasyon büyüklüğü
olarak kullanılacaksa (WP4'te olacak) mod seçicisinin polarizasyonu da
sabitlemesi gerekir. Ayrıca üç satırın `2.367` değeri referansın `2.402`
değerinden `0.035` sapıyor; bu, farklı düzlem yüksekliği/PML kurgusundan gelen
ayrıklaştırma farkı, fizik değil. `n_eff` nihai bir çıktı olarak
raporlanacaksa ızgara yakınsaması ayrıca yapılmalıdır.

## Yan bulgu — kuplaj tasarımı için önemli

Modun gücünün yalnızca `%60–63`'ü çekirdekte; gerisi evanescent kuyruklarda.
Bus-ring kuplajı `0.2 µm` gap üzerinden bu kuyrukla kurulduğu için bu oran
`Q_e` hesabında doğrudan rol oynar ve WP4'ün ihtiyaç duyduğu
geometri → `Q_e` eşlemesinin girdisidir.

## Geriye kalan şüpheli

Rezonans dışı `%12–23` eksik güç açıklanmadı. İki şüpheli elendi:

- BOX sızıntısı → bu belgede çürütüldü
- İzlenmeyen drop portu → rezonans dışında drop bus'ta yalnız `0.0006` var;
  dört-port düzeltmesi rezonanstaki `%69`'u açıklar, rezonans dışını açıklamaz

**Kalan en güçlü şüpheli: kaynak ve monitör düzlemleri waveguide'ın kesilmiş
uç yüzlerinde.** Bus `x = -8 … +8`, domain `±9`; kılavuz `±8`'de bitiyor ve
arkasında PML'e kadar 1 µm oksit var. `mode:bus_through:in` tam o uç yüzde
enjekte ediyor, `flux:bus_through:out` öbür uç yüzde topluyor. Sonlandırılmış
bir facette enjeksiyon, kılavuza hiç girmeyen geri radyasyon üretir ve dalga
boyuna bağlı bir baseline düşüşü verir — ölçülen eğimli baseline
(`0.774` → `0.884`, 3 nm içinde) bununla uyumludur.

Bu şüpheli de ücretli koşu açmadan sınanabilir: `_port_plane`'in uç yüzden
içeri bir margin ile çalışması, ya da bus'ı domain'den kısa tutmak yerine
uçları PML içine sokmak. Her ikisi de geometri/kod düzeyinde, FDTD gerektirmez
ancak doğrulaması bir koşu ister.
