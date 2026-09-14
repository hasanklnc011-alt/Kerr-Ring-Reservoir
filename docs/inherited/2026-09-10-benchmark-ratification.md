# ADR — NARMA-10 benchmark ratifikasyonu

- Tarih: 2026-09-10
- Karar sahibi: Astra/Codex
- Durum: Kabul edildi

## Ratifiye edilen sözleşme

- Klasik NARMA-10 nüksü: order 10, `alpha=0.3`, `beta=0.05`, `gamma=1.5`,
  `delta=0.1`; sürüş `u ~ Uniform[0, 0.5)`.
- Kanonik yürütme ortamı: CPython 3.14.7, NumPy 2.4.6, SHA-256 türetilmiş seed
  ve PCG64 akışı.
- Development manifest: `1b865944b5f99eeb8f408121760fe0f5f178b7eb58aae24e47401c7bdd13d482`
  (5 seed).
- Blind manifest: `6cc96caac8f6244207e4f0d2c82cea2c5ad6138c25ebc5a9e8ebddd3d78eb4ea`
  (10 seed).

## Kanıt

`preflight` sekiz kontrolü geçti: manifestolar yeniden üretildi, seedlerin tamamı
sonlu, dev/blind digestleri ayrık ve candidate lock yokken kör değerlendirme
erişilemez. Kanonik test paketi 82/82 geçti.

## Korunan sınır

Bu ratifikasyon blind evaluation veya candidate lock oluşturmaz. Aday kodu ve
konfigürasyonu geliştirme aşaması sonunda hash'lenene kadar blind manifest
okunmayacak ve kör skor aday seçimine geri beslenmeyecek.
