# Proje sözleşmesi

## Araştırma kapsamı

Kerr odaklı, platform-bağımsız halka reservoir. İlk adaylar Si3N4/SiO2 ve
AlGaAsOI, 1550 nm; bunlar kabul edilmiş platformlar değil, sınanacak adaylardır.
Topoloji: tek halka ve doğrudan kuplajlı iki halka. Serbest piksel/topoloji
optimizasyonu başlangıçta yoktur.

Güç tavanı: çip girişinde toplam ortalama 10 mW, tepe 100 mW. Bu bir araştırma
tavanıdır, malzeme güvenlik sınırı değildir; daha düşük kaynaklı sınır önceliklidir.

Giriş/readout: tek optik giriş, sembol başına 20 sabit mask slotu, iki fiziksel
çıkış gücü = 40 özellik. Maske ilk skordan önce kilitlenir.

## Ön kapılar (Plan 2'den önce, 0 FC)

- **G1 — mode solver sağlığı.** Aynı tanı kodu Si ve SiN kesitlerinde koşulur.
  Eski hattı durduran `n_eff` %3 salınımının kök nedeninin araç mı yoksa yüksek
  indeks kontrastı mı olduğu ayrılır. Sonuç, platform seçimini gerekçelendirir
  ya da aracın Plan 2'de kullanılamayacağını gösterir.
- **G2 — bellek üçgeni.** Kerr anlık olduğundan bellek foton ömründen gelir.
  `Q`, `T_sym`, giriş gücü ve NARMA-10'un istediği geçmiş derinliği arasındaki
  fizibilite bölgesi kapalı formda çıkarılır. Boş çıkarsa Kerr-only hattı durur.

Bu iki kapı geçmeden Plan 2 P3 taraması ve Angler tasarım işi başlamaz.

## Başarı ve durma

Başarı: kilitli tek aday üzerinde 10 kör seed medyan NMSE <0.05 ve >=8/10 <0.05.
Geliştirme: 5 seed; 200/3000/2000 split ve mevcut veri hash'leri korunur.

Durma: kaynaklı güçte görev avantajı yok; 2B–3B normalizasyon kurulamıyor;
gerçek dışı parametreyle kazanç; dayanıklılık başarısız; 3B kanıt bütçeye sığmıyor;
G1 veya G2 ön kapısı boş çıkıyor.

Kapsam dışı: fabrikasyon, deneysel başarı, hazır üretim PDK'sı, global surrogate.

## Yürütme

Aşamalar: [Plan 2 ADR](decisions/2026-09-14-plan2-kerr-reservoir.md).
Devralınanlar ve eski depoyla sınır: [migrasyon kaydı](decisions/2026-09-14-repo-migration.md).

## Araştırma hattı bağlantıları

- [[🏰 300-Projects/Photonic-Reservoir/spiral-delay-reservoir/MayOS/Photonic-Reservoir|Önceki Photonic Reservoir hattı]]
- [[🧠 500-Knowledge/concepts/Photonic-Research-Lines-Synthesis|Fotonik araştırma hatları sentezi]]
- [[⚔️ 200-Goals/Micro-Ring-Reservoir-Computing|Micro-Ring Reservoir Computing hedefi]]
