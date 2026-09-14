# G1 — mode solver sağlık kontrolü

Üretim komutları:

```bash
./.venv-mode-211/Scripts/python.exe -m fdtd.modes env
./.venv-mode-211/Scripts/python.exe -m fdtd.modes diagnose --grid uniform --output reports/g1/mode-diagnostic-subpixel-uniform.json
./.venv-mode-211/Scripts/python.exe -m fdtd.modes diagnose --grid auto    --output reports/g1/mode-diagnostic-subpixel-auto.json
```

Kod: `fdtd/modes/` · Testler: `python -m tests.fdtd.run_tests`
Karar kaydı: [2026-09-14-g1-mode-solver](../../docs/decisions/2026-09-14-g1-mode-solver.md)

## 0. Sonuç

**G1 GEÇTİ.** Her iki kesitte, her iki grid tipinde dört kapının dördü de
geçiyor — *subpixel ortalaması açıkken*.

Kök neden **eksik subpixel ortalaması**. `GridSpec.auto`'nun grid çizgilerini
yapı sınırlarına yaslaması bağımsız bir hata değil, bu eksikliği görünür kılan
**yükselteç**: arayüz grid düzlemine oturduğunda hücre ataması tek bir kayan
nokta eşitliğine kalıyor ve `1e-12 µm` öteleme atamayı topluca çeviriyor.

Mode solver sağlam. Reddedilmesi gereken bir araç değil, eksik olan bir ayardı.

## 1. Dört koşunun tablosu

Aynı solver, aynı geometri, aynı seçici, aynı kapılar. Değişen yalnız iki şey.

| subpixel | grid | kesit | `n_eff` yayılımı | bağıl | mesh kapısı (26→32) | en kötü `1e-12 µm` Δ | sonuç |
|---|---|---|---|---|---|---|---|
| **ON** | uniform | Si | 2.53e-03 | %0.107 | 6.77e-04 | 0 | **PASS** |
| **ON** | uniform | SiN | 3.29e-03 | %0.183 | 7.17e-05 | 0 | **PASS** |
| **ON** | auto | Si | 2.58e-03 | %0.110 | 5.32e-04 | 4.0e-15 | **PASS** |
| **ON** | auto | SiN | 1.52e-04 | %0.008 | 2.86e-05 | 1.1e-15 | **PASS** |
| OFF | uniform | Si | 2.79e-02 | %1.214 | 6.37e-03 | 0 | sonuçsuz |
| OFF | uniform | SiN | 7.40e-03 | %0.412 | 3.75e-03 | 2.4e-05 | sonuçsuz |
| OFF | auto | Si | 2.86e-02 | %1.211 | 2.86e-02 | 2.9e-14 | sonuçsuz |
| OFF | auto | SiN | 1.66e-02 | %0.923 | 7.29e-03 | **5.9e-03** | sonuçsuz |

Okunacak üç şey:

1. **Subpixel açıkken yayılım 11 kata kadar küçülüyor** (Si: %1.21 → %0.107) ve
   mesh kapısı geçiliyor. Subpixel kapalıyken hiçbir kombinasyon geçmiyor.
2. **Auto grid'in patolojisi subpixel ile tamamen kayboluyor.** Öteleme
   duyarlılığı `5.9e-03`'ten `1.1e-15`'e (makine hassasiyeti) düşüyor.
   Yani uniform grid bir *çare* değil, yalnız hasarı azaltan bir önlemdi.
3. **Uniform grid tek başına yetmiyor.** Subpixel kapalıyken monotonluğu ve
   öteleme kararlılığını geri getiriyor ama `n_eff` yakınsamıyor
   (mesh kapısı `6.4e-03`, eşik `1e-03`).

## 2. Subpixel açık, uniform grid — merdiven

| spw | `n_eff` (Si) | `n_g` (Si) | `n_eff` (SiN) | `n_g` (SiN) |
|---|---|---|---|---|
| 16 | 2.352078497 | 4.14036 | 1.800477529 | 2.09452 |
| 20 | 2.353198520 | 4.14443 | 1.803770749 | 2.09480 |
| 26 | 2.353928871 | 4.14753 | 1.802383425 | 2.09369 |
| 32 | 2.354605619 | 4.14864 | 1.802311771 | 2.09486 |

Si için `n_g → 4.1486`; eski depodaki `20 spw → 4.145` gözlemiyle tutarlı.
Seçilen mod her koşuda `mode_index 0`, TE `0.978–0.998`, çekirdek hapsi Si'de
`0.59–0.60`, SiN'de `0.84–0.86`.

## 3. Kontrast hipotezi

Subpixel kapalıyken kontrast hatayı ölçekliyordu (Si yayılımı SiN'in 3.8 katı).
Subpixel açıkken Si hâlâ daha büyük artık hata taşıyor (mesh kapısı `5.3e-04`
vs SiN `2.9e-05`, ~18 kat) **ama ikisi de rahatça geçiyor**.

Yani kontrast artık hatanın büyüklüğünü belirliyor, fizibiliteyi değil.
**Plan 2'nin platform değişimi bu bulguyla gerekçelenmiyor.** §2'de kurduğum
"SiN geçer, Si geçmez" beklentisi yanlış çıktı: doğru ayarla ikisi de geçiyor.

## 4. Ortam

Local subpixel `tidy3d-extras` gerektiriyor ve **2.12.0 bu makinede çalışmıyor**.
PE import tablosu karşılaştırmasıyla kesinleştirildi:

| wheel | yerel modüller | ek bağımlılık |
|---|---|---|
| 2.12.0 | `extension`, `_isolated_extension` | `_isolated_extension` → `libomp140.x86_64.dll` |
| 2.11.x | yalnız `extension` | `VCOMP140.DLL` |

`libomp140.x86_64.dll` LLVM'in OpenMP çalışma zamanı; Microsoft onu yalnız
Visual Studio içinde `debug_nonredist` klasöründe dağıtıyor ve **yeniden
dağıtılamaz** olarak işaretliyor. Makinede Visual Studio yok. `VCOMP140.DLL`
ise Microsoft'un kendi OpenMP çalışma zamanı, sıradan VC++ redistributable'ın
parçası ve `C:\Windows\System32`'de zaten mevcut.

Bu yüzden ortam **2.11.2'ye sabitlendi** ve hiçbir sistem değişikliği
yapılmadı. Ayrıntı: `requirements/README.md`.

Ortam kapısı sürümden bağımsız: aynı küçük yüksek-kontrast çözümü flag kapalı
ve açık koşup **sonucun değişmesini** şart koşuyor. Kabul edilip yok sayılan
bir flag da kapıyı geçemiyor. Ölçülen etki 2.11.2'de `1.17e-01`.

## 5. Seçici

Eski seçicinin kusuru (en yüksek `n_eff`'i almak) giderildi: bir mod ancak
`TE ≥ 0.8` **ve** çekirdek güç hapsi `≥ 0.5` ise aday. Hiçbiri geçmezse ya da
iki aday `1e-3` içinde dejenereyse fonksiyon **hata veriyor** — geri düşüş yok.

## 6. Sınırlar

- **Eski scriptler yeniden çalıştırılmadı** (gitignore'da, eski depoda).
  İddia "eski kusur kanıtlandı" değil; "aynı imza kontrollü kurulumda üretildi
  ve doğru ayarla yok edildi"dir.
- Malzeme indisleri standart çalışma figürleri, kaynaklı değil (P1).
- Yerel mode solver uzak çözücüyle karşılaştırılmadı; kapı yerel yakınsama
  kapısıdır, mutlak doğruluk kanıtı değildir.
- Örtüşme metriği pozitif bir L2 benzerliğidir; güç ortogonalliği veya
  bağımsız fizik doğrulaması değildir.
- Tek kesit, düz kılavuz. Bend, kuplaj ve supermode ayrı işlerdir.

## 7. Etki

- Yerel mode solver kullanılabilir; **subpixel ortalaması zorunlu ayardır.**
- Windows'ta yerel mode işi için `tidy3d 2.11.2` sabitlenmeli.
- Eski depodaki "tüm yerel solver kullanılamaz" hükmü yanlıştı; "Q_i kesin
  sayısal kayıptır" ve "Q_bend > 3e7" hükümleri ise bu çalışmayla
  *sınanmadı* — ayrı işler olarak açık kalıyor.
