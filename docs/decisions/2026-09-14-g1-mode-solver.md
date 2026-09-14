# G1 — mode solver sağlık kontrolü: kök neden grid şartnamesi

- Durum: **KISMEN KAPALI.** Kök neden bulundu ve gösterildi; kapı `libomp140.x86_64.dll`
  eksikliği nedeniyle AÇIK kaldı. 2026-09-14.
- Sahip: Claude (kod/test).
- Rapor: [studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md](../../studies/plan2-kerr/G1-MODE-DIAGNOSTIC.md)
- Ham kayıtlar: `reports/g1/mode-diagnostic-nosubpixel.json`, `reports/g1/mode-diagnostic-autogrid.json`

## Bulgu

Eski silikon hattını durduran `n_eff` salınımının kaynağı mode solver değil,
**grid şartnamesi**. `GridSpec.auto` grid çizgilerini yapı sınırlarına yaslar.
Arayüz bir grid düzlemine denk geldiğinde ve subpixel ortalaması yokken, bir
hücre sırasının malzeme ataması tek bir kayan nokta eşitliğine kalır; yapıyı
`1e-12 µm` ötelemek bu atamayı topluca çevirir.

Kontrollü karşılaştırma (aynı solver, geometri, seçici; yalnız grid değişiyor):

| | Si yayılımı | Si monoton mu | SiN en kötü `1e-12 µm` Δ |
|---|---|---|---|
| uniform grid | 2.79e-02 | evet | 2.4e-05 |
| auto grid | 2.86e-02 | **hayır** | **5.9e-03** |

Auto grid'de Si'nin aykırı noktası 26 spw; eski raporun aykırı noktası da
26 spw idi. SiN'de 26 spw'deki öteleme sıçraması eski depodaki
`2.298684 → 2.364882` olayının aynısıdır.

## Etkisi

- **Mode solver reddedilmemeli.** Uniform grid ve fiziksel mod seçici ile
  monoton yakınsıyor; `n_g` son iki mesh arasında `%0.18` değişiyor.
- Üretimde arayüz-hassas ölçümlerde `GridSpec.auto` kullanılmamalı ya da
  subpixel ortalaması zorunlu tutulmalı.
- **Plan 2'nin platform değişimi bu bulguyla gerekçelenmiyor.** İndeks
  kontrastı hatayı 3.8 kat büyütüyor ama etkiyi yaratmıyor: auto grid'de
  sorun SiN'de de var. Kontrast büyüklüğü belirler, varlığı değil.
- Eski depodaki dört hipotezin (mod seçici, substrate hibritleşmesi, PML
  kalınlığı, supermode kurgusu) hepsinin çürümesi bu mekanizmayla tutarlı;
  hiçbiri grid yaslanmasını içermiyordu.

## Kapıyı kapatmayan şey

Local subpixel bu makinede çalışmıyor. Kök neden PE import tablosu
karşılaştırmasıyla kesinleştirildi: `tidy3d_extras._isolated_extension`
**`libomp140.x86_64.dll`** (LLVM OpenMP) istiyor, DLL makinede yok; MSVC
çalışma zamanı mevcut. Bu yüzden her iki koşu da `subpixel_active: false`,
`gate_valid: false` olarak kayıtlı ve **hiçbiri G1 kapısını kapatmıyor**.

Ortam kapısı (`python -m fdtd.modes env`) bunu kanıtlayarak durur; sessiz
geri düşüş yok. `--allow-no-subpixel` yalnız açıkça sonuçsuz kayıt üretir.

DLL'i güvenilir bir kaynaktan edinmek (ör. Visual Studio yükleyicisinin
LLVM/clang bileşeni) Hasan'ın ortam kararıdır; rastgele bir siteden tek
başına DLL indirilmeyecek.

## Kanıt

- `fdtd/modes/`: `environment.py` (ortam kapısı), `cross_sections.py`,
  `solver.py` (uniform/auto grid, sabit ızgarada öteleme), `selection.py`
  (TE + çekirdek hapsi; en yüksek `n_eff`'e geri düşüş YOK, dejenere çiftte
  hata), `overlap.py`, `diagnose.py`, `cli.py`.
- `tests/fdtd/` 36/36: seçicinin yüksek-`n_eff` substrate modunu reddetmesi,
  hiçbir aday yokken hata vermesi, kapıların subpixel'siz koşuyu
  geçirmemesi, örtüşmenin global faz/ölçek altında değişmemesi ve dik
  bileşenlerde sıfır olması, kayıtlı koşuların tutarlılığı (uniform'da Si
  monoton, auto'da değil; auto'da öteleme duyarlılığı geri geliyor).
- Ortam kilidi: `requirements/g1-mode.in`, `requirements/g1-mode-win-py314.lock.txt`,
  `requirements/README.md`.

## Açık

- G1 kapısı: subpixel ile aynı merdiveni koş ve dört kapıyı değerlendir.
- Malzeme indisleri standart çalışma figürleri, kaynaklı değil (P1).
- Eski scriptler yeniden çalıştırılmadı; iddia "bu mekanizma aynı imzayı
  üretiyor ve kontrollü kurulumda yok ediliyor"dur, "eski kusur kanıtlandı"
  değil.
