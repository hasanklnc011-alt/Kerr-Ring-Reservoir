# Ajan operasyon rehberi

Bu dosya ve `CLAUDE.md` her değişiklikte birlikte güncellenir.
Kanonik sabitler: `const.md`. Sıra: `BACKLOG.md`.

## Roller

- **Claude** — kod, test ve uygulama kanıtı sahibi.
- **Codex** — yalnız hedef, sözleşme, karar ve değerlendirme dokümantasyonu.
- Aynı dosyada eşzamanlı yazma yok; devir `BACKLOG.md` üzerinden.

## Kanıt merdiveni

Bir sayı ancak kaynağı ve geçtiği kapı yazıldığında iddia olur:

1. `synthetic` — yalnız sentetik/analitik testte kullanılabilir.
2. `source-supported` — birincil kaynak, birim, dalga boyu, sıcaklık ve
   proses/geometri bağlamıyla birlikte kayıtlı.
3. `EM-supported` — bu geometrinin EM ölçümünden, yakınsama kanıtıyla.
4. `unresolved` — eksik. Sessiz varsayılanla doldurulmaz, NMSE'ye uydurulmaz.

Kurallar:
- Farklı cihazların en iyi özellikleri tek hayalî cihazda birleştirilmez.
- İki mesh farkı güven aralığı değildir.
- Aynı koşunun iki portu bağımsız yöntem değildir.
- İteratif yakınsama fiziksel kararlılıkla eşdeğer değildir.
- Lineer sonuç nonlinear kanıt değildir.
- Ablation tek başına üstünlük değildir; yeniden optimize edilmiş kontrol ayrıca raporlanır.

## Kör suite

Kör suite bu depoda tek kopyadır. G0 kapanana kadar gerçek kör değerlendirme
çalıştırılmaz. Suite tek nihai aday üzerinde bir kez tüketilir; kör sonuçtan
sonra tuning yoktur. Farklı aday kimliği suite'i yeniden açamaz.

## Bütçe

Her ücretli solve: canlı bakiye okuması + yazılı estimate + Hasan'ın açık onayı.
60 FC taban, 25 FC tek koşu tavanı, 20 FC final rezerv. B25 OPEN olduğu sürece
yeni ücretli solve yoktur. Bütçe eski depoyla ortaktır.

## Teslimat biçimi

Her teslimat: küçük commit, çalışan test, kaynak/geometri/solver hash'leri,
parametre için birim–köken–belirsizlik–kabul durumu, üretim komutu ve güncel
backlog satırı. Başarı iddiası yalnız geçen kapıya aittir.

## Git

Normal push `origin/main`; force-push yok; uzak SHA doğrulanır.
API anahtarları, ham HDF5 ve büyük artifact'ler Git'e eklenmez.
