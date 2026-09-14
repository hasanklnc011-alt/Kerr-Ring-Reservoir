# G2 — Kerr bellek üçgeni

Üretim komutu: `python -m plan2_kerr.screen --boundary`
Kod: `plan2_kerr/memory_triangle.py` · Testler: `python -m tests.plan2_kerr.run_tests` (41/41)
Karar kaydı: [2026-09-14-g2-memory-triangle](../../docs/decisions/2026-09-14-g2-memory-triangle.md)

Bu bir **tarama**dır, fiziksel kabul değildir. Malzeme girdilerinin neredeyse
tamamı `unresolved` (P1 açık). Aşağıdaki baş sonuç ise hiçbir malzeme sabiti
içermez ve bu yüzden P1'den bağımsız olarak geçerlidir.

## 1. Neden bir üçgen var

Kerr **anlıktır**: nonlinearite sağlar, bellek sağlamaz. Kerr-only bir halkada
tek bellek mekanizması kavite enerji sönümüdür. Dolayısıyla görevin istediği
geçmiş derinliği, sembol süresi ve yüklü Q üç bağımsız serbestlik değil, tek
bir kısıt yüzeyidir.

`m` sembol önce giren enerjinin kalan kesri `exp(-κ m T_sym)`, `κ = ω₀/Q_L`.
Bu kesrin en az `ε` olmasını istersek:

```
Q_L ≥ m · ω₀ · T_sym / ln(1/ε)
```

Sembol başına `N` mask slotu ve sürücü/dedektör bant genişliği `B` ile
`T_sym = N/B` olduğundan:

```
Q_floor = m · ω₀ · N / ( ln(1/ε) · B )
```

**Bu ifadede hiçbir malzeme sabiti yok.** Yüksek `n₂` bu tabanı düşürmez;
platform seçimi belleği satın alamaz. `n₂` yalnız izin verilen güçte yeterli
nonlinearite alınıp alınmadığını belirler.

## 2. Plan 2'nin nominal ayarında sonuç

Girdi: NARMA-10 (`m = 10`), Plan 2 maskesi (`N = 20`), `B = 50 GHz`,
`ε = 1/e`, 1550 nm.

| Büyüklük | Değer |
|---|---|
| Slot süresi | 20 ps |
| Sembol süresi | 400 ps (2.5 GBaud) |
| **Q_floor (yüklü)** | **4.86 × 10⁶** |
| Gerekli intrinsic Q (kritik kuplaj) | 9.72 × 10⁶ |
| İzin verilen kayıp, `n_g = 2.0` | **0.036 dB/cm** |
| İzin verilen kayıp, `n_g = 3.8` | 0.069 dB/cm |

Foton ömrü burada `τ_ph = m·T_sym = 4 ns`.

### Aday platformlar

| Platform | Q_L tavanı | Bellek | Taşıyabildiği slot | Gereken B | Taşıyabildiği derinlik |
|---|---|---|---|---|---|
| Si₃N₄/SiO₂ (0.1 dB/cm, kaynaksız) | 1.76 × 10⁶ | ✗ | 7.2 | 138 GHz | 3.6 sembol |
| AlGaAsOI (Q_i = 3.52 × 10⁶, kaynaklı) | 1.76 × 10⁶ | ✗ | 7.2 | 138 GHz | 3.6 sembol |

İki satırın aynı çıkması tesadüftür: `0.1 dB/cm` ve `n_g = 2.0` tam olarak
`Q_i = 3.52 × 10⁶` verir, AlGaAsOI'nin ölçülmüş değeriyle aynı sayı. Kopyala-
yapıştır hatası değildir.

**Nominal ayarda fizibilite bölgesi her iki adayda da BOŞ.** Darboğaz
nonlinearite değil, **bellek**: 20 slotluk maske sembolü 400 ps'ye uzatıyor ve
bu da 4 ns'lik foton ömrü, yani Q_L ≈ 5 × 10⁶ istiyor.

## 3. Bölgeyi ne açar

`Q_floor` üç şeye doğrusal bağlı. Duyarlılık:

| ε | slot | B | T_sym | Q_floor | Q_i gerekli | maks kayıp (n_g=2.0) |
|---|---|---|---|---|---|---|
| 1/e | 20 | 50 GHz | 400 ps | 4.86e6 | 9.72e6 | 0.036 dB/cm |
| 1/e | 20 | 100 GHz | 200 ps | 2.43e6 | 4.86e6 | 0.072 dB/cm |
| 1/e | 10 | 50 GHz | 200 ps | 2.43e6 | 4.86e6 | 0.072 dB/cm |
| 1/e | 10 | 100 GHz | 100 ps | 1.22e6 | 2.43e6 | 0.145 dB/cm |
| 1/e | 5 | 50 GHz | 100 ps | 1.22e6 | 2.43e6 | 0.145 dB/cm |
| 1/e | 5 | 100 GHz | 50 ps | 6.08e5 | 1.22e6 | 0.29 dB/cm |
| 0.01 | 20 | 50 GHz | 400 ps | 1.06e6 | 2.11e6 | 0.167 dB/cm |
| 0.01 | 10 | 50 GHz | 200 ps | 5.28e5 | 1.06e6 | 0.334 dB/cm |
| 0.01 | 5 | 100 GHz | 50 ps | 1.32e5 | 2.64e5 | 1.33 dB/cm |

Üç kaldıraç var:

1. **Slot sayısını düşürmek.** En güçlüsü ve en ucuzu. 20 → 5 slot `Q_floor`'u
   dörtte bire indirir. Bedeli: sembol başına özellik sayısı düşer
   (`N × port`), yani readout kapasitesi azalır.
2. **Bant genişliğini artırmak.** 50 → 100 GHz tabanı yarıya indirir, ama
   "erişilemeyen modülatör/dedektör hızı kabul edilmez" kuralına çarpar.
3. **`ε`'u gevşetmek.** `1/e → 0.01` tabanı 4.6 kat düşürür. Ama bu fiziksel
   bir kazanç değil, bir **modelleme seçimidir**: `ε` gerçekte "10 sembol
   sonraki artık, readout gürültü tabanının üstünde mi" sorusudur. Gürültü ve
   ADC çözünürlüğü modellenmeden `ε` seçmek tabanı keyfî kılar. **Bu G2'nin
   en zayıf halkasıdır ve P2'de kapatılmalıdır.**

## 4. Nonlinearite tarafı

Bellek geçilirse nonlinearite kapalı formda:

```
γ = 2π n₂ / (λ₀ A_eff)          [1/(W·m)]
F = Q_L λ₀ / (n_g · 2πR)
ρ_Kerr = γ · F² · R · P_in / π   [linewidth]
```

Kritik kuplajda `P_circ/P_in ≈ F/π` yaklaşımı kullanıldı; yaklaşım olduğu
kodda kayıtlı.

İki sonuç dikkat çekici:

- `ρ_Kerr ∝ Q_L²`. Bellek de Q istediğinden **ikisi aynı yöne çekiyor**;
  klasik "bellek-nonlinearite gerilimi" bu mimaride yok.
- `F² R ∝ 1/R`. Sabit Q'da **büyük halka nonlinearite için daha kötü**.
  Oysa ultra-düşük kayıplı SiN'de yüksek Q genellikle büyük yarıçapla
  geliyor. Gerçek gerilim burada: kayıp bütçesi büyük halka istiyor,
  Kerr küçük halka istiyor. Bu, P4'ün asıl tasarım sorusudur.

## 5. Termal

Aynı build-up, ama **soğurulan** güçle. `ρ_th` hesaplanabilmesi için kaybın
soğurulan kesri (`α_abs`) ve cihazın termal direnci (`R_th`) gerekiyor;
ikisi de yok. Kod bu durumda tahmin üretmiyor, `None` döndürüyor.

Zaman ölçeği notu: `τ_th` mikrosaniye mertebesinde, `T_sym` ise 400 ps.
Termal kayma **ortalama** gücü izler; sembol başına bellek üretmez, çalışma
noktasında yarı-statik bir kaymadır. Ama çok linewidth'lik bir kayma da
kilitlenmeyi zorunlu kılar ve bistabilite riski taşır. "Kerr reservoir"
adlandırması bu terimi görünmez kılmamalı.

## 6. G2 kabul durumu

BACKLOG kabul ölçütü: *"her aday platform için fizibilite bölgesinin boş olup
olmadığı sayıyla gösterilir"*. Gösterildi:

- Plan 2'nin **nominal** ayarında bölge iki adayda da **boş**.
- Bölge prensipte boş değil; `Q_floor ≤ Q_ceiling` koşulunu sağlayan ayarlar
  var ve §3'te sayıyla listelendi.
- Karar `n₂`'ye değil, **erişilebilir intrinsic Q'ya ve slot sayısına**
  bağlı. Bu, platform tartışmasını P1'den önce yeniden çerçeveler.

## 7. Sınırlar

- Tek modlu, tek halkalı, kritik kuplajlı, rezonansta çalışan bir kavite
  varsayıldı. İki bağlı halka farklı bir taban verir (ayrı iş).
- `ε` seçimi gürültü modeli olmadan keyfî (§3).
- `F/π` build-up ve `Q_i = 2πn_g/(λα)` standart yaklaşımlardır.
- `Si₃N₄` satırındaki tüm malzeme sayıları `unresolved`; yalnız AlGaAsOI
  `Q_i = 3.52 × 10⁶` kaynaklıdır
  (Xie ve ark., Opt. Express 28(22), 32894 (2020), arXiv:2004.14537; özet
  2026-09-14'te okundu).
- Bu tarama hiçbir kapıyı fiziksel olarak kapatmaz; P1 kaynak tablosunu
  ikame etmez.
