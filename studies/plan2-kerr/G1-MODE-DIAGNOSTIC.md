# G1 — mode solver sağlık kontrolü

Üretim komutları:

```bash
./.venv-mode/Scripts/python.exe -m fdtd.modes env
./.venv-mode/Scripts/python.exe -m fdtd.modes diagnose --allow-no-subpixel --grid uniform --output reports/g1/mode-diagnostic-nosubpixel.json
./.venv-mode/Scripts/python.exe -m fdtd.modes diagnose --allow-no-subpixel --grid auto    --output reports/g1/mode-diagnostic-autogrid.json
```

Kod: `fdtd/modes/` · Testler: `python -m tests.fdtd.run_tests` (36/36)
Karar kaydı: [2026-09-14-g1-mode-solver](../../docs/decisions/2026-09-14-g1-mode-solver.md)

## 0. Baş sonuç

Eski hattı durduran `n_eff` salınımının kök nedeni **mode solver değil, grid
şartnamesi.** `GridSpec.auto` grid çizgilerini yapı sınırlarına yaslıyor;
arayüz tam bir grid düzlemine denk geldiğinde, subpixel ortalaması yokken bütün
bir hücre sırasının malzeme ataması kayan nokta eşitliğine kalıyor. Yapıyı
`1e-12 µm` ötelemek bu atamayı topluca çeviriyor.

Yapıdan bağımsız **uniform** grid'de aynı solver, aynı geometri, aynı seçici ile
salınım kayboluyor ve `n_eff` monoton yakınsıyor.

Bu, G1'in BACKLOG'da öngörülen iki şıkkının da dışında üçüncü bir cevap:
**araç bozuk değil, kurulum yanlıştı.**

## 1. Ortam kapısı

`fdtd/modes/env` local subpixel'in gerçekten çalıştığını kanıtlamaya çalışır ve
çalışmıyorsa durur. Bu makinede durum:

```
tidy3d 2.12.0 · tidy3d-extras 2.12.0 · Python 3.14.7 · Windows 11
local subpixel  UNAVAILABLE
reason          tidy3d_extras native worker will not load: DLL load failed
```

Kök neden PE import tablosu karşılaştırmasıyla kesinleştirildi: iki yerel
uzantıdan yalnız `_isolated_extension` **`libomp140.x86_64.dll`** (LLVM OpenMP
çalışma zamanı) istiyor ve bu DLL makinede hiç yok. MSVC çalışma zamanı mevcut,
yani eksik olan özellikle OpenMP. Ayrıntı: `requirements/README.md`.

**Bu yüzden aşağıdaki koşular G1 kapısını KAPATMAZ.** Hepsi
`subpixel_active: false`, `gate_valid: false` olarak kayıtlı. Ama kök neden
sorusunu subpixel olmadan da cevaplıyorlar — çünkü karşılaştırma, subpixel'in
yokluğunda iki grid tipi arasında.

## 2. Uniform grid (yapıdan bağımsız)

`dl = λ₀ / (spw · n_core)`, yapı konumundan bağımsız.

| spw | dl (nm) | n_eff (Si) | ±1e-12 µm Δ | n_eff (SiN) | ±1e-12 µm Δ |
|---|---|---|---|---|---|
| 16 | 27.84 / 48.53 | 2.299468914 | 0 | 1.795905824 | 0 |
| 20 | 22.27 / 38.83 | 2.310727699 | 0 | 1.803304522 | 0 |
| 26 | 17.13 / 29.87 | 2.321015702 | 0 | 1.798506635 | 0 |
| 32 | 13.92 / 24.27 | 2.327388983 | 0 | 1.802252666 | 2.4e-05 |

- **Si monoton artıyor.** Yayılım `2.79e-02` (%1.21) — subpixel yokluğunda
  beklenen yavaş birinci mertebe yakınsama.
- SiN yayılımı `7.40e-03` (%0.41), Si'nin **3.8 katı küçüğü** — indeks
  kontrastıyla ölçekleniyor.
- Öteleme testi neredeyse tümüyle sıfır: arayüzler grid çizgilerine denk
  gelmediği için sonsuz küçük kayma hiçbir hücreyi çevirmiyor.
- `n_g` (Si) 4.0994 → 4.1301, son iki mesh arası değişim `%0.18`. Eski
  depodaki `20 spw → 4.145` değeriyle tutarlı.

## 3. Auto grid (yapı sınırlarına yaslanan)

Aynı solver, aynı geometri, aynı seçici; yalnız `GridSpec.auto`.

| spw | n_eff (Si) | ±1e-12 µm Δ | n_eff (SiN) | ±1e-12 µm Δ |
|---|---|---|---|---|
| 16 | 2.366257743 | 2.9e-14 | 1.809460996 | 6.7e-16 |
| 20 | 2.363305017 | 5.8e-15 | 1.811971361 | 6.7e-16 |
| 26 | **2.387601090** | 8.0e-15 | **1.795405969** | **5.9e-03** |
| 32 | 2.359042019 | 3.6e-15 | 1.802693437 | 4.4e-16 |

- **Monotonluk yok.** Si'de 26 spw dışarı fırlıyor — eski raporda da
  aykırı nokta 26 spw idi (2.2987).
- SiN'de 26 spw'de `1e-12 µm` öteleme `n_eff`'i **`5.9e-03`** değiştiriyor.
  Eski depodaki `2.298684 → 2.364882` olayı tam olarak bu: belirli
  çözünürlüklerde arayüz grid düzlemine oturuyor.
- Mesh-mesh mod örtüşmesi Si'de `0.9857`'ye düşüyor (uniform'da `0.9995`):
  yalnız `n_eff` değil, mod profilinin kendisi de zıplıyor.

## 4. Yorum

Üç gözlem birlikte tutarlı tek bir hikâye veriyor:

1. Auto grid arayüzlere çizgi yaslar → arayüz grid düzlemindedir.
2. Subpixel ortalaması yoktur → hücrenin malzemesi tek bir eşitlik kararıyla
   belirlenir.
3. Sonsuz küçük öteleme bu kararı topluca çevirir → `n_eff` sıçrar, ve
   çözünürlük değiştikçe hangi arayüzün hangi düzleme denk geldiği
   değiştiğinden yakınsama monoton olmaz.

Uniform grid 1. adımı kırdığı için etki kayboluyor. Subpixel ortalaması
2. adımı kıracaktır — standart çözüm budur, ama bu makinede henüz sınanamadı.

Eski depodaki dört hipotez (mod seçici, substrate hibritleşmesi, PML fiziksel
kalınlığı, supermode kurgusu) bu mekanizmanın hiçbirini içermiyordu; hepsinin
çürümesi tutarlı.

## 5. Ne kanıtlanmadı

- **Eski scriptler yeniden çalıştırılmadı.** Onlar gitignore'da ve eski
  depoda. Buradaki iddia "eski kusur bu mekanizmadır" değil, "bu mekanizma
  aynı imzayı üretiyor ve kontrollü kurulumda yok edilebiliyor"dur.
- **Subpixel'in etkiyi kaldırdığı gösterilmedi** — `libomp140.x86_64.dll`
  eksik. G1 kapısı bu yüzden hâlâ AÇIK.
- İndeks kontrastı hipotezi **çürütülmedi ama ikincil**: uniform grid'de
  yayılımı 3.8 kat ölçekliyor, fakat auto grid'de etki iki platformda da var.
  Yani kontrast büyüklüğü belirliyor, varlığı değil.
- Malzeme indisleri standart çalışma figürleri; kaynaklı değil (P1).

## 6. Sonuç ve etki

- **Mode solver reddedilmemeli.** Uniform grid + fiziksel mod seçici ile
  düzgün davranıyor.
- **Üretimde `GridSpec.auto` arayüz-hassas ölçümlerde kullanılmamalı**, ya da
  subpixel ortalaması zorunlu tutulmalı.
- Plan 2'nin platform değişimi bu bulguyla **gerekçelenmiyor**: sorun
  silikonun yüksek kontrastı değildi. Kontrast yalnız hatayı büyütüyordu.
- G1 kapısını kapatmak için gereken tek şey `libomp140.x86_64.dll`.

## 7. Seçici ve örtüşme

Eski seçicinin kusuru (en yüksek `n_eff`'i almak) giderildi: bir mod ancak
`TE ≥ 0.8` **ve** çekirdek güç hapsi `≥ 0.5` ise aday. Hiçbiri geçmezse veya
iki aday `1e-3` içinde dejenereyse fonksiyon **hata veriyor** — geri düşüş yok.
Bu koşularda seçilen mod her zaman `mode_index 0`, TE `0.979–0.999`,
çekirdek hapsi Si'de `0.60`, SiN'de `0.86`.

Örtüşme metriği sözleşmedeki tanımdır; pozitif bir L2 benzerliğidir, güç
ortogonalliği veya bağımsız fizik doğrulaması değildir.
