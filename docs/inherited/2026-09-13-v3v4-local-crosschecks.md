> Güncel geçerlilik: [Kurtarma ADR](2026-09-13-optical-chain-recovery-plan.md).
> Aşağıdaki tarihsel iddialar güncel parametre kabulü yerine kullanılamaz.

# 2026-09-13 — V3/V4 yerel çapraz kontroller: 1 geçti, 3 sorun açtı

- Yapan: Claude Opus 5
- Maliyet: **0 FlexCredit** (tamamı yerel mode solver)
- Amaç: `OPTICAL-PARAMETER-STATUS.md`'deki V3/V4 boşluklarını kapatmak

Boşluklar kapanmadı. Bunun yerine merdiven, FDTD değerlerinin sanılandan daha
kırılgan olduğunu gösterdi. Aşağıdakiler olumsuz sonuçlardır ve öyle
raporlanmaktadır.

## ✅ 1. FSR çaprazlaması — GEÇTİ

```
n_eff = 2.36698   n_g = 4.14516        (group_index_step, yerel)
halka cevresi 2*pi*4.775 = 30.0022 um
ONGORULEN FSR = lam^2/(n_g*L) = 19.091 nm
OLCULEN   FSR = 18.93 nm     ->  fark %0.85
```

Mode solver'ın verdiği `n_g` ile 3B FDTD'nin gördüğü rezonans aralığı `%0.85`
içinde uyuşuyor. **`n_eff`/`n_g` için V3 kapandı.** İki tamamen bağımsız yol —
biri kesit mod çözümü, diğeri tam dalga spektrumu — aynı sayıyı veriyor.

## ⚠️ 2. Bend radyasyon `Q_i` — ölçülemedi, ama önemli bir şey söylüyor

```
R=4.775 um   k_eff=6.349e-08   Q_bend = 32 644 563
R=6.000 um   k_eff=5.502e-08   Q_bend = 37 668 172
R=8.000 um   k_eff=4.935e-08   Q_bend = 41 997 611
```

Bend radyasyonu yarıçapla **üstel** azalmalıdır. Yarıçap `1.7x` büyürken
`Q_bend` yalnız `%29` değişiyor — bu üstel değil, düz. Yani `k_eff ~ 6e-08`
fiziksel radyasyon değil, **çözücünün gürültü tabanı** (BOX taramasındaki
`-1.2e-08 / +4.3e-08` ile aynı mertebe).

Doğru okuma: **bend radyasyonu ölçülemeyecek kadar küçük**, `Q_bend > ~3e7`.
Bu bir alt sınırdır, ölçüm değil.

### Ve bu, `Q_i` hakkındaki asıl sorunu açığa çıkarıyor

Modelde malzemeler **kayıpsız** (`conductivity = 0`) ve bend radyasyonu
**ihmal edilebilir**. O hâlde bu simülasyonda halkanın fiziksel intrinsic
kaybı **yok denecek kadar azdır** ve `Q_i` çok büyük olmalıdır.

Oysa 3B FDTD transmisyonundan çıkardığımız `Q_i` değerleri `3.8e4 – 7.1e4`
mertebesindeydi. Arada **~1000 kat** fark var.

**Sonuç: 3B FDTD'de gördüğümüz "intrinsic kayıp" fiziksel değil, sayısaldır.**
Bu, `freq-rung-3`'te kayıp kanallarının (`T_add +54%`, `T_through +43%`)
yakınsamamasını da açıklıyor — yakınsamayan şey fizik değil, ayrıklaştırma
artefaktı.

### Bunun ADR'ye etkisi — bir düzeltme gerekiyor

ADR (`2026-09-13-adr-tcmt-primary-fdtd-calibrator.md`) `Q_i`'yi "yalnızca
full-wave ölçümünden gelir" listesine koymuştu. **Bu, kayıpsız malzeme modeli
için yanlıştır**: ölçülecek bir şey yoktur. Fiziksel `Q_i` ancak gerçek kayıp
mekanizmaları modele **konulursa** (sidewall roughness saçılması, malzeme
absorpsiyonu) anlam kazanır — ve Astra'nın taslağı bunları zaten doğru biçimde
"FDTD tek başına üretmez" listesine koymuştu.

Yani `Q_i`, `n2`/TPA/carrier ömürleri ile aynı kategoridedir: kaynaklı girdi,
FDTD çıktısı değil.

## ❌ 3. `Q_e` çapraz yolu — GEÇMEDİ, iki yol `3.7x` ayrı

```
n_even = 2.58128   n_odd = 2.55310   dn = 2.817e-02
kappa   = pi*dn/lam            = 0.05744 1/um
gamma   = 8.7231 1/um          L_eff = sqrt(pi*R/gamma) = 1.3114 um
kappa^2 = sin^2(kappa*L_eff)   = 0.00566
Q_e(supermode) = pi*n_g*L/(lam*kappa^2) = 44 774
Q_e(FDTD)      = 12 180 +- %1.3          ->  fark %268
```

Hangisinin doğru olduğunu **bu veriyle ayırt edemiyorum**. İki taraf da
zayıf noktalar taşıyor:

- **Supermode tarafı:** `L_eff = sqrt(pi*R/gamma)` standart ama kaba bir
  yaklaşımdır. Ayrıca bükülmüş halka modu ile düz bus modu arasındaki faz
  uyumsuzluğu hesaba katılmadı — bu, gerçek `kappa^2`'yi **daha da
  küçültür**, yani `Q_e`'yi daha da büyütür ve farkı kapatmaz, açar.
- **FDTD tarafı:** `Q_e = Q_L/sqrt(T_drop)` simetrik kuplaj ve tek modlu TCMT
  varsayıyor; üstelik `Q_L`'nin kendisi yakınsamadı (`%6.56`) ve kayıp
  kanallarının sayısal olduğu yukarıda görüldü.

**V3, `Q_e` için düşüyor.** `Q_e = 12 180 ± %1.3` ifadesindeki `%1.3`
yalnızca mesh yakınsamasını yansıtıyordu; **yöntem belirsizliği bunun çok
üstünde**, en az `3x` mertebesinde.

## ❌ 4. `n_eff` ızgara yakınsaması — GEÇMEDİ, salınıyor

```
16 step/lam -> n_eff = 2.370158
20 step/lam -> n_eff = 2.366977   degisim -0.1342%
26 step/lam -> n_eff = 2.298684   degisim -2.8853%
32 step/lam -> n_eff = 2.363790   degisim +2.8323%
```

Tek düze yakınsama yok; `26 step/λ` noktası aykırı. Bu, fizik değil **benim
mod seçicimin kararsızlığıdır**: çekirdek-güç ölçütü, farklı çözünürlüklerde
farklı modu (muhtemelen farklı polarizasyon veya hibrit bir substrate modu)
seçiyor. Aynı kararsızlığı daha önce BOX taramasında `2.0 µm` satırında da
görmüştüm ve orada not düşmüştüm; şimdi sistematik olduğu anlaşıldı.

**Aracım güvenilir değil.** Düzeltilmesi ücretsiz: mod seçicisi polarizasyon
fraksiyonunu (`TE`/`TM`) ve simetriyi de sabitlemeli.

## Genel durum — dürüst özet

| iş | sonuç |
|---|---|
| FSR çaprazlaması | ✅ `%0.85` — `n_eff`/`n_g` için V3 kapandı |
| bend `Q_i` | ⚠️ gürültü tabanı; `Q_bend > 3e7`, ölçüm değil alt sınır |
| supermode `Q_e` | ❌ iki yol `3.7x` ayrı, V3 düştü |
| `n_eff` V4 | ❌ salınıyor, mod seçici kararsız |

Bu oturumun en önemli çıktısı olumsuz olanı: **kayıpsız malzeme modelinde
`Q_i` ölçülemez** ve bugüne kadar `Q_i` diye raporladığımız sayı sayısal
kaybın ölçüsüydü. `Q_e` de sanıldığı kadar sağlam değil.

Yakınsamış ve çapraz doğrulanmış tek büyüklükler: **`lambda_0`, `n_eff`, `n_g`**.

## Sonraki adımlar — hepsi `0 FC`

1. **Mod seçicisini sabitle** (polarizasyon + simetri), `n_eff` V4'ünü tekrarla.
2. **`Q_e` uyuşmazlığını daralt**: faz uyumsuzluğunu içeren bir halka-bus
   kuplaj hesabı, ya da `L_eff` yerine gap boyunca `kappa(z)` integrali.
   Kapanmazsa `Q_e` geniş belirsizlikle raporlanır.
3. **ADR'yi düzelt**: `Q_i` "FDTD'nin yetkili olduğu" listeden çıkarılıp
   "kaynaklı girdi" listesine taşınmalı — Hasan'ın onayı gerekir, çünkü
   `const.md`'ye dokunuyor.
4. `reports/OPTICAL-PARAMETER-STATUS.md` bu sonuçlarla güncellendi.

Hiçbiri yeni FDTD koşusu gerektirmiyor.
