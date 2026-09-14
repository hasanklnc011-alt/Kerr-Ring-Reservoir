# G1 — mode solver sağlık kontrolü: kök neden eksik subpixel ortalaması

> **DÜZELTME 2026-09-15:** Aşağıdaki "dört kapı da geçti" sonucu **tek bir grid
> hizalamasında** ölçülmüştür. Hizalama ekseni test edilmemişti ve orada etki
> `1.4e-2` — mesh kapısının 14 katı. Mesh inceltmek bunu çözmüyor (salınım
> `dl` 2.5 kat inerken yalnız 1.87 kat düşüp duruyor). Üretim değeri artık
> **dört ofsetin ortalamasıdır**. Bkz.
> [hücre-altı hizalama kararı](2026-09-15-g1-subcell-alignment.md).
> Özgün metin tarihçe olarak korunmuştur.


- Durum: **KAPALI (GEÇTİ)**, 2026-09-14.
- Sahip: Claude (kod/test).
- Rapor: [studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md](../../studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md)
- Ham kayıtlar: `reports/g1/mode-diagnostic-subpixel-{uniform,auto}.json` (kapı),
  `reports/g1/mode-diagnostic-{nosubpixel,autogrid}.json` (kontrol, sonuçsuz)

## Karar

Yerel mode solver **kabul edilir**; kullanım koşulu subpixel ortalamasının
açık olmasıdır. Dört kapı (öteleme, mesh, grup indisi, mod örtüşmesi) hem
`Si-450x220` hem `SiN-1200x800` için, hem uniform hem auto grid'de geçti.

## Bulgu

Eski hattı durduran `n_eff` salınımının kök nedeni **eksik subpixel
ortalaması**. `GridSpec.auto`'nun grid çizgilerini yapı sınırlarına yaslaması
bağımsız bir hata değil, bu eksikliğin **yükselteci**: arayüz grid düzlemine
oturduğunda hücrenin malzeme ataması tek bir kayan nokta eşitliğine kalıyor ve
`1e-12 µm` öteleme atamayı topluca çeviriyor.

| subpixel | grid | Si yayılımı | SiN en kötü öteleme Δ | sonuç |
|---|---|---|---|---|
| ON | uniform | 2.53e-03 (%0.107) | 0 | PASS |
| ON | auto | 2.58e-03 (%0.110) | 1.1e-15 | PASS |
| OFF | uniform | 2.79e-02 (%1.214) | 2.4e-05 | sonuçsuz |
| OFF | auto | 2.86e-02 (%1.211) | **5.9e-03** | sonuçsuz |

Üç okuma:

1. Subpixel açıkken yayılım 11 kata kadar küçülüyor ve mesh kapısı geçiliyor.
2. Auto grid'in öteleme duyarlılığı subpixel ile `5.9e-03` → `1.1e-15`
   (makine hassasiyeti) oluyor; grid seçimi yalnız subpixel yokken önemliydi.
3. Uniform grid tek başına yetmiyor: monotonluğu geri getiriyor ama `n_eff`
   yakınsamıyor (mesh `6.4e-03`, eşik `1e-03`).

## Kontrast hipotezi — kısmen yanlış

Subpixel kapalıyken kontrast hatayı 3.8 kat ölçekliyordu. Açıkken Si hâlâ ~18
kat daha büyük artık hata taşıyor ama **ikisi de rahatça geçiyor**. Kontrast
hatanın büyüklüğünü belirliyor, fizibiliteyi değil.

**Plan 2'nin platform değişimi bu bulguyla gerekçelenmiyor.** "SiN geçer, Si
geçmez" beklentisi yanlış çıktı.

## Ortam kararı

`tidy3d-extras==2.12.0` bu makinede local subpixel yapamıyor:
`_isolated_extension` **`libomp140.x86_64.dll`** (LLVM OpenMP) istiyor, o da
Microsoft tarafından yalnız Visual Studio içinde ve **yeniden dağıtılamaz**
olarak dağıtılıyor; makinede Visual Studio yok. `2.11.x` ise Microsoft'un
kendi `VCOMP140.DLL`'ini kullanıyor ve o zaten `System32`'de mevcut.

Karar: G1 ortamı **`tidy3d==2.11.2` + `tidy3d-extras==2.11.2`** olarak
sabitlendi. Hiçbir sistem değişikliği yapılmadı, rastgele kaynaktan DLL
indirilmedi. Cloud işi gerekirse ayrı bir venv'de tutulacak.

Ortam kapısı sürümden bağımsız hale getirildi: aynı küçük yüksek-kontrast
çözümü flag kapalı ve açık koşup sonucun değişmesini şart koşuyor. Kabul
edilip yok sayılan bir flag de kapıyı geçemez.

## Eski hükümler

"Tüm yerel mode solver kullanılamaz" hükmü **yanlıştı**, geri alınıyor.
"Q_i kesin sayısal kayıptır" ve "Q_bend > 3e7" hükümleri bu çalışmada
**sınanmadı**; ayrı işler olarak açık kalıyor.

## Kanıt

- `fdtd/modes/`: `environment.py` (ampirik subpixel kanıtı), `cross_sections.py`,
  `solver.py` (uniform/auto grid, sabit ızgarada `1e-12 µm` öteleme),
  `selection.py` (TE + çekirdek hapsi; en yüksek `n_eff`'e geri düşüş YOK,
  dejenere çiftte hata), `overlap.py`, `diagnose.py`, `cli.py`.
- `tests/fdtd/`: seçici, kapılar, örtüşme metriği ve dört kayıtlı koşunun
  tutarlılığı.
- Ortam: `requirements/g1-mode.in`, `requirements/g1-mode-win-py314.lock.txt`,
  `requirements/README.md`.
- Ücretli solve yok; tüm koşular yerel, 0 FC.

## Sınırlar

Eski scriptler yeniden çalıştırılmadı; iddia "aynı imza kontrollü kurulumda
üretildi ve doğru ayarla yok edildi"dir. Yerel çözüm uzak çözücüyle
karşılaştırılmadı: kapı yerel yakınsama kapısıdır, mutlak doğruluk kanıtı
değildir. Tek kesit, düz kılavuz; bend, kuplaj ve supermode ayrı işlerdir.
Malzeme indisleri standart çalışma figürleri, kaynaklı değil (P1).
