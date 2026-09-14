# ADR — Kanonik NARMA-10 benchmark seçimi

- Tarih: 2026-09-10
- Karar sahibi: Astra/Codex
- Durum: Kabul edildi

## Karar

`benchmarks/narma10_np/` tek kanonik yerel NARMA-10 benchmark uygulamasıdır.
Eşzamanlı Claude dağıtımından oluşan standart-kütüphane çoğaltısı kaldırıldı.

## Gerekçe

Kanonik uygulama, yalnız seed listesi yerine hem giriş hem hedef dizilerini
SHA-256 ile kilitler; candidate-lock'a blind manifesto özetini bağlar; aday
başına tek blind sonucu append-only ledger ile zorlar. Bunlar kör testin tuning'e
geri beslenmesini stdlib çoğaltısından daha sıkı engeller. NumPy 2.4.6 mevcut
yerel ortamda doğrulandı; bu benchmark henüz Tidy3D/FDTD veya cloud bağımlılığı
taşımaz.

## Kanıt

`python -m unittest discover -s tests -p 'test_*.py' -v` ile iki iskelet
birlikteyken 119 test geçti. Tekilleştirme sonrasında kanonik paket için aynı
komutun 66 test geçmesi gerekir. Dev/blind manifestoları `verify-manifests`
ile yeniden üretildi; sırasıyla 5 ve 10 seed sonlu, blind küme henüz açılmadı.

## Açık kapı

Manifestolar bütünlük bakımından doğrulanmıştır fakat Astra ratifikasyonu ve
aday kilidi olmadan blind evaluation kesinlikle başlatılamaz.
