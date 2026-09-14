> Güncel geçerlilik: [Kurtarma ADR](2026-09-13-optical-chain-recovery-plan.md).
> Aşağıdaki tarihsel iddialar güncel parametre kabulü yerine kullanılamaz.

# 2026-09-13 — Çapraz kontrol onarımları: ÖN KAYIT (sonuçlar görülmeden yazıldı)

- Yapan: Claude Opus 5
- Maliyet: `0 FlexCredit`
- Kural: `AGENTS.md` V3 — *bir çapraz yol uyuşmazlığı bulunduğunda, yapılacak
  düzeltme uyuşmayı kontrol etmeden önce yazılır.*

Bu belgenin **§Tahminler** bölümü, hesaplar çalıştırılmadan önce yazılmıştır.
Sonuçlar §Sonuçlar bölümüne eklenecek ve tahminlerle karşılaştırılacaktır.

## Onarım 1 — mod seçici

**Kusur:** seçici yalnız çekirdek güç oranına bakıyor ve farklı
çözünürlüklerde farklı modu seçiyor (`n_eff` V4 salınımı; BOX taramasında
`2.0 µm` aykırılığı).

**Düzeltme:** seçici artık (a) polarizasyon fraksiyonunu (`TE` baskın) ve
(b) çekirdek güç oranını birlikte kullanacak; ayrıca seçilen modun `n_eff`'i
bir önceki çözünürlükteki değere en yakın olan olacak (süreklilik takibi).

Bu, FDTD'ye uydurma değildir — aracın kendi hatasının giderilmesidir ve
FDTD'ye hiç bakılmadan da yapılması gerekirdi.

**Tahmin:** düzeltilmiş seçiciyle `n_eff`, `16 → 32 step/λ` boyunca tek düze
ve `%0.5`'ten küçük değişimle yakınsayacak; `26 step/λ` aykırılığı kaybolacak.

## Onarım 2 — `Q_e` faz uyumsuzluğu

Şimdiye kadar iki hata düzeltildi (ikisi de sonuçtan bağımsız doğrulanabilir):

- **A:** `L_eff = sqrt(pi*R/gamma)` → `sqrt(2*pi*R/gamma)`. Gerekçe: aralık
  profili `g(z) ≈ g0 + z²/(2R)` olduğundan `∫exp(-γz²/2R)dz = sqrt(2πR/γ)`.
  Aritmetik hata.
- **B:** `gamma`'da even supermode indeksi yerine **tek** waveguide `n_eff`'i.
  Gerekçe: aralıktaki alan sönümünü tek kılavuzun modu belirler.

Bunlar `Q_e`'yi `44 750 → 19 660`'a indirdi (FDTD'ye oran `3.67x → 1.61x`).

**Şimdi eklenecek — C:** bükülmüş halka modu ile düz bus modu arasındaki faz
uyumsuzluğu. Gauss profilli kuplajda katsayı
`exp(-Δβ² R / (2γ))` ile çarpılır, `Δβ = k0 (n_ring − n_bus)`.

**Tahmin (C):** `n_ring = 2.36863` (R=4.775 bend) ve `n_bus = 2.36698` ölçüldü,
yani `Δn ≈ 1.65e-03` — çok küçük. Faz uyumsuzluğu çarpanının `1`'e çok yakın
çıkmasını, dolayısıyla `Q_e`'yi **ihmal edilebilir ölçüde artırmasını**
bekliyorum. Yani **kalan `1.6x` uyuşmazlığını KAPATMAYACAK**, hatta çok az
açacak.

Bu tahmini şimdiden yazıyorum ki, C uyuşmayı kapatırsa bunun sürpriz olduğu
belli olsun.

## Onarım 3 — kontrol: `kappa`'nın gap bağımlılığı

**Amaç:** supermode yolunun kendisinin sağlamasını yapmak (V2).
`kappa` gap ile **üstel** azalmalıdır. `gap = 0.15 / 0.20 / 0.25 / 0.30 µm`
için `kappa` hesaplanacak ve `ln(kappa)` vs `gap` doğrusal mı bakılacak.

**Tahmin:** `ln(kappa)` gap'e karşı doğrusal çıkacak ve eğimi `−2γ ≈ −15.3 1/µm`
mertebesinde olacak. Çıkmazsa supermode yolu güvenilmez demektir ve `Q_e`
tartışmasında ağırlığı düşer.

## Kabul edilen sınır — peşinen

Kalan uyuşmazlığı kapatmak için **gerekçesiz bir çarpan konulmayacaktır.**
A, B, C ve kontrol uygulandıktan sonra fark sürerse, `Q_e` iki yolu da
kapsayan bir **aralıkla** raporlanacaktır. Belirsizliği yazmak meşru,
yok etmek için uydurmak değildir.

## EK ÖN KAYIT — Onarım 4 (Onarım 1 çürüdükten sonra yazıldı)

Onarım 1'in tahmini **tutmadı**: düzeltilmiş seçici (polarizasyon + süreklilik)
her dört çözünürlükte de aynı modu buluyor (`mode#7`, `TE %97-98`, çekirdek
`%58-62`) ama `n_eff` yine `26 step/λ`'da `2.2987`'ye sıçrıyor. Yani kusur
seçicide değil, çözümün kendisinde.

**Yeni hipotez:** kesit düzlemindeki `2 µm` Si substrate, `n_eff` ekseninde
sıkışık bir mod ailesi taşıyor; bu modların konumu ayrıklaştırmayla kayıyor ve
biri waveguide moduna yaklaştığında **hibritleşme (anti-crossing)** oluyor.
Destekleyen gözlem: doğru mod BOX taramasında `mode#5`, burada `mode#7` —
substrate modları indeks sırasını sürekli değiştiriyor.

**Tahmin (Onarım 4):** substrate tamamen kaldırılıp aynı tarama
(`16/20/26/32 step/λ`) tekrarlandığında `n_eff` **tek düze** ve toplam yayılım
**`%0.5`'ten küçük** olacak; `26 step/λ` sıçraması kaybolacak.

Çıkmazsa bu hipotez de düşer ve sorun mode solver kurgusunun daha temel bir
yerindedir.

---

## Sonuçlar

**Dört tahminin üçü çürüdü, biri tuttu.**

### Tahmin 1 (mod seçici) — ÇÜRÜDÜ

```
16 step/lam -> mode#7 n_eff=2.370158 TE=98% cekirdek=60%
20 step/lam -> mode#7 n_eff=2.366977 TE=98% cekirdek=61%   -0.1342%
26 step/lam -> mode#7 n_eff=2.298684 TE=97% cekirdek=58%   -2.8853%
32 step/lam -> mode#7 n_eff=2.363790 TE=98% cekirdek=62%   +2.8323%
yayilim %3.0416   tek duze: False
```

Düzeltilmiş seçici her çözünürlükte **aynı** modu buluyor (`mode#7`, TE baskın,
çekirdekte yoğun) — yani seçim tutarlı. Buna rağmen `n_eff` sıçraması aynen
duruyor. Kusur seçicide değil.

### Tahmin 4 (substrate hibritleşmesi) — ÇÜRÜDÜ

```
SUBSTRATE YOK:
16 step/lam  2.303831            26 step/lam  2.392483  (+1.0482%)
20 step/lam  2.367666 (+2.7708%) 32 step/lam  2.389093  (-0.1417%)
yayilim %3.7512   tek duze: False
```

Substrate tamamen kaldırıldı; salınım sürüyor, hatta yayılım biraz arttı.
Substrate de kusurun kaynağı değil.

### Tahmin 2 (faz uyumsuzluğu ihmal edilebilir) — TUTTU

```
n_ring=2.368634  n_bus=2.366977  dn=1.656e-03  dbeta=0.00675 1/um
faz uyumsuzlugu carpani = exp(-dbeta^2*R/(2*gamma)) = 0.99998576
```

Çarpan `1`'e `1.4e-05` yakınlıkta; `Q_e`'yi ölçülebilir biçimde değiştirmedi ve
uyuşmazlığı kapatmadı — tam öngörüldüğü gibi.

### Tahmin 3 (`kappa` gap'e üstel bağlı) — ÇÜRÜDÜ, ve en ağırı bu

```
gap=0.15 um  n_even=2.61291 n_odd=2.58138  kappa=0.06429 1/um
gap=0.20 um  n_even=2.61281 n_odd=2.58128  kappa=0.06429 1/um
gap=0.25 um  n_even=2.61269 n_odd=2.58115  kappa=0.06429 1/um
gap=0.30 um  n_even=2.61257 n_odd=2.58104  kappa=0.06430 1/um

ln(kappa) vs gap egim = +0.0006 1/um   beklenen -15.29   fark %100
```

Gap iki katına çıkarken `kappa` altı hanede sabit. Fiziksel olarak imkânsız.

Ayrıca `n_even = 2.613` ve `n_odd = 2.581`, tek waveguide'ın `2.367`'sinin
**ikisi de çok üstünde**. İki özdeş kılavuzun even/odd supermodları `2.367`'nin
hemen altında ve üstünde olmalıydı. Yani seçilen modlar even/odd supermodları
**değil**.

## GERİ ÇEKME — `Q_e` "çapraz yol uyuşmazlığı" iddiası geçersiz

`docs/decisions/2026-09-13-v3v4-local-crosschecks.md` §3'te "iki yol `3.7x`
ayrı" denmişti; ardından `L_eff` ve `gamma` düzeltmeleriyle `1.61x`'e indirildi.

**Bunların hepsi geçersizdir.** İki geçerli yöntem uyuşmuyor değildi; ikinci
yöntem hiç çalışmıyordu. `kappa` doğru mod çiftinden alınmadığı için ortada bir
çapraz yol yoktu. `L_eff` düzeltmeleri (A, B) aritmetik olarak doğruydu ama
yanlış bir `kappa` üzerine uygulandı; bu koşudaki `Q_e = 15 718` sayısı da
dayanaksızdır.

Kontrol testi (V2) bunu yakaladı — ama **bu kontrol ilk `Q_e` hesabı
raporlanmadan önce yapılmalıydı.** Yapılmadığı için iki tur boyunca dayanaksız
bir sayı ve ondan türetilmiş bir uyuşmazlık analizi sunuldu.

## Durum

Üç hipotez arka arkaya çürüdü (seçici, substrate, ve supermode yolunun kendisi).
Bu, kusurun tek bir bileşende değil **yerel mode solver kurgusunun genelinde**
olduğunu gösteriyor.

Kalan en somut şüpheli: `num_pml` **hücre** cinsinden veriliyor, dolayısıyla
çözünürlük arttıkça PML'in **fiziksel kalınlığı küçülüyor** (`16 sl`'de
`~0.8 µm`, `32 sl`'de `~0.4 µm`). İnce PML daha kötü soğurur ve modu bozar;
bu, "mesh inceldikçe düzelmiyor, salınıyor" davranışını doğrudan açıklar.

**Sınama ön kaydı:** `num_pml` çözünürlükle orantılı ölçeklenip PML fiziksel
kalınlığı sabit tutulacak. Tahmin: yakınsama tek düze ve yayılım `%0.5` altı.

**Durma kuralı:** bu da tutmazsa daha fazla hipotez denenmeyecek; yerel mode
solver yolu güvenilmez ilan edilip V3, `n_eff`/`n_g` dışında **kapanmamış**
bırakılacaktır. FSR çaprazlaması geçerliliğini korur, çünkü tek çözünürlükteki
`n_g`'yi FDTD'nin bağımsız ölçümüyle karşılaştırır ve `%0.85` tutmuştur.


---

## SON SINAMA — PML kalınlığı hipotezi de ÇÜRÜDÜ, durma kuralı devrede

```
A) num_pml=12 sabit (PML fiziksel kalinligi kuculuyor)
  16 sl  npml=12  dy=27.3 nm  PML=0.328 um  ->  n_eff=2.370158
  20 sl  npml=12  dy=21.9 nm  PML=0.263 um  ->  n_eff=2.366977
  26 sl  npml=12  dy=16.9 nm  PML=0.203 um  ->  n_eff=2.298684
  32 sl  npml=12  dy=13.8 nm  PML=0.165 um  ->  n_eff=2.363790
  yayilim %3.0416  tek duze: False

B) num_pml=12*spw/16 (PML fiziksel kalinligi SABIT ~0.33 um)
  16 sl  npml=12  PML=0.328 um  ->  n_eff=2.370158
  20 sl  npml=15  PML=0.329 um  ->  n_eff=2.366977
  26 sl  npml=20  PML=0.338 um  ->  n_eff=2.298684
  32 sl  npml=24  PML=0.330 um  ->  n_eff=2.363790
  yayilim %3.0416  tek duze: False

TAHMIN: B'de yayilim <%0.5 ve tek duze  ->  TUTMADI
```

İki kol **altı hanede birebir aynı**. `num_pml` `12 → 24`'e çıkarıldığında
sonuç kılpayı bile değişmedi. Bu yalnız hipotezi çürütmekle kalmıyor, ayrıca
`ModeSpec.num_pml`'in bu kurguda **etkisiz** olduğunu düşündürüyor.

**Durma kuralı uygulandı.** Beşinci hipotez denenmeyecek.

## Hüküm: yerel mode solver yolu güvenilmez

Dört hipotez arka arkaya çürüdü — mod seçici, substrate hibritleşmesi,
supermode kuplaj hesabı, PML kalınlığı. Ortak sonuç: bu kurgudaki yerel mode
solver, yakınsama çalışması için **kullanılamaz**. `n_eff` çözünürlükle `%3`
salınıyor ve nedeni bulunamadı.

### Bu, FSR çaprazlamasını da zayıflatıyor

`n_eff`/`n_g` için V3'ün geçtiğini (`%0.85`) raporlamıştım. O `n_g`, **tek bir
çözünürlükte** (`20 step/λ`) hesaplanmıştı. `n_eff` çözünürlükle `%3`
salındığına göre `n_g` de benzer biçimde salınır; `26 step/λ`'nın değeri
kullanılsaydı öngörülen FSR `%3` kayardı ve `%0.85` uyum bozulurdu.

Yani **tek V3 geçişimiz de koşulludur**: `20 step/λ` seçimine bağlı, ve o
seçimin gerekçesi yok. Uyumun bir kısmı şans olabilir.

## Geriye ne kaldı

Yerel mode solver'dan bağımsız olarak ayakta duran tek büyüklük:

- **`lambda_0 = 1.54090 ± 0.00008 µm`** — iki FDTD portundan, mode solver'a
  hiç dokunmadan; ayrıca `12 → 14 step/λ` mesh yakınsamasını `%0.42` FSR ile
  geçti.

`Q_L` mesh belirsizliğiyle (`%7`) duruyor ama çapraz yolu yok.
`Q_e`, `Q_i`, `n_eff`, `n_g` için güvenilir bir ikinci yol **yok**.

## Sonuç — WP4 ve bütçeye etkisi

Plan, geometri → `Q_e` eşlemesinin **ücretsiz yerel mode solver ile**
kurulacağını varsayıyordu (`reports/FLEXCREDIT-LEDGER.md` tahsis planı:
"`Q_i/Q_e/n_eff` ikinci yolları — `0 FC`"). **Bu varsayım artık geçersizdir.**

Üç seçenek kalıyor:

1. **Ücretli FDTD ile surrogate**: geometri taramasının her noktası 3B FDTD
   ister. Kalan `115.7 FC` ile ancak birkaç nokta alınır; tarama kurulamaz.
2. **Başka bir araç**: MEEP veya bağımsız bir mode solver (örn. `femwell`,
   `EMpy`). Kurulum ve doğrulama maliyeti var ama FlexCredit harcamaz.
   Ayrıca bağımsız bir araç, V3 için gerçek bir ikinci yol sağlar.
3. **Tidy3D'nin uzak mode solver'ı**: yerel çözücünün uyardığı
   "subpixel averaging ile daha iyi doğruluk" seçeneği. Ücretlidir ama 3B
   FDTD'den çok ucuzdur; yerel çözücüdeki kusurun subpixel eksikliğinden
   gelip gelmediğini de doğrudan test eder.

**Önerim 3 → 2 sırası:** önce uzak mode solver'ı tek bir noktada dene
(ucuz, ve yerel/uzak farkı kusurun kaynağını söyler); kusur orada yoksa
tarama uzak solver ile yapılabilir. Çıkmazsa bağımsız açık kaynak araca geç.

Bu, Hasan'ın kararını gerektirir çünkü tahsis planını değiştirir.
