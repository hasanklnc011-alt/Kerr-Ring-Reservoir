# Plan 2 — Düşük güçte Kerr odaklı halka reservoir tasarımı

Durum: kullanıcı tarafından kabul edilmiş araştırma planı; bu teslimat dokümantasyondur.
Kod/test sahibi Claude; Codex plan, sözleşme ve değerlendirme dokümantasyonu.
Plan 2 ayrı araştırma kaydıdır; mevcut silikon kurtarma hattını değiştirmez.
Plan 1 adı Uğur Hocaya göndermelik araç önerisini ifade eder; mevcut K0–K5
silikon kurtarma hattı ile otomatik olarak eşanlamlı değildir.
Bütün hatlar ortak bütçe ve ortak kör suite kısıtına tabidir.

## 1. Amaç ve temel kararlar

Araştırma sorusu: Halka geometrisini ve kuplajını tasarlayarak erişilebilir optik
güçte görev açısından yararlı Kerr nonlinearlığı ve zamansal bellek elde edilebilir mi?

Nihai hedef: EM ile desteklenen adayda kilitli 10 kör NARMA-10 seed medyanı
<0.05 ve en az 8/10 seed <0.05. Başarısızlık, nedenleri ve fizibilite sınırlarıyla
geçerli araştırma çıktısıdır; başarı kapısı geçirilmiş sayılmaz.

- Kerr odaklı platform; mevcut silikon kesitine bağlılık yok.
- Tek halka ve doğrudan birbirine kuplajlı iki halka; halka topolojisi korunur.
- Başlangıçta serbest piksel/topoloji optimizasyonu yok.
- Çip girişinde toplam ortalama 10 mW, tepe 100 mW araştırma tavanı.
  Bunlar malzeme güvenlik sınırı değildir; daha düşük kaynaklı sınır önceliklidir.
- Sembol süresi optimize edilebilir; erişilemeyen modülatör/detector hızı kabul edilmez.
- Fabrikasyon, deneysel başarı ve hazır üretim PDK'sı kapsam dışıdır.
- Angler nonlinear bileşen; zaman modeli görev; FEMwell kesit/normalizasyon;
  RONN mimari referansı. Ceviche ve SAX yalnız gerekçeli ihtiyaç halinde eklenir.

## 2. P0 — Araştırma ve benchmark sınırı, 0 FC

Ayrı çalışma alanı, deney kimlikleri, provenance ve araç sürümü kayıtları oluştur.
Mevcut veri üretimi, 200/3000/2000 split ve 5 geliştirme seed'i korunur.
Ortak K2s işi gerçek scorer, paket bütünlüğü ve atomik suite tüketimini kapatmadan
gerçek kör değerlendirme yoktur. Plan 1, Plan 2 ve mevcut kurtarma hattı ayrı
aday kimlikleriyle aynı suite'i yeniden kullanamaz. Geliştirme sonunda seçilen
tek nihai adaya bir kez açılır. Eski testler yeni modelin kabul kanıtı değildir.

Teslimat: bu sözleşme, benchmark protokolü, gerçek araç sürümleri ve deney kayıt biçimi.
Dokümantasyonun yayımlanması tek başına P0 teknik kabulü değildir.

## 3. P1 — Malzeme ve güç fizibilitesi, 0 FC

İlk adaylar Si3N4/SiO2 ve AlGaAs-on-insulator; başlangıç 1550 nm.
Bunlar kabul edilmiş uygun platformlar değildir. Her adayda:

- Lineer indis/dispersiyon, Kerr, lineer kayıp, nonlinear absorpsiyon ve gerekli termal girdileri kaynaklandır.
- Kesit, yarıçap ve kaybın aynı proses/geometri bağlamını paylaşıp paylaşmadığını yaz.
- Farklı cihazların en iyi özelliklerini tek hayalî cihazda birleştirme.
- Ortalama/tepe güç, alan yoğunluğu ve ölçüm bant genişliğini birlikte değerlendir.
- Kaynaklı Kerr rezonans kayması/linewidth oranını tahmin et; küçük oran tek başına eleme değildir.
- Önemli nonlinear absorpsiyon/termal değişimi modele ekle; Kerr-only ile fiziksel kabul verme.

Kaynak kapsamı yeterli platformlarda eşit P3 taraması yapılır. Geliştirme kapısını
geçen adaylar arasında düşük toplam giriş gücü; eşitlikte basit mimari ve geniş
tolerans bölgesi seçilir. P1 kaynak kapısı P3'ten önce, nihai platform seçimi P3
sonrasında kapanır; kaynak incelemesi ile platform seçimi birbirine karıştırılmaz.
Hiçbiri fizibilite göstermezse üçüncü platforma otomatik geçilmez.

## 4. P2 — Dinamik çekirdek, 0 FC

Her halka kompleks optik alan; kaynaklı geri saçılma varsa CW/CCW.
|a|² enerji, |s|² güç; enerji sönümü kappa, alan sönümü kappa/2.
Kerr frekans kayması, port kuplajı ve kayıp ayrı terimlerdir. Platformun gerekli
absorpsiyon/carrier/termal durumları eklenir. İki halka kuplajı karşılıklı ve
enerjiyle tutarlıdır. Kaynaksız nonlinear katsayı yalnız sentetik testte kullanılır.

Giriş/readout:
- Tek optik giriş, sembol başına 20 sabit mask slotu.
- Tüm mimarilerde aynı maske, ilk skordan önce kilitli.
- İki fiziksel çıkış gücü slot sonunda örneklenir: 40 özellik.
- Eşit detector/özellik bütçesi; iç alan/carrier/sıcaklık readout'a verilmez.
- Semboller-arası dijital tap yok; ridge yalnız train iç ayrımıyla seçilir.

Kontroller: input-only, belleksiz PD, aynı lineer optik yapı+PD, Kerr kapalı,
tam model; 0/1/5/10/20 geçmiş örnekli dijital baseline ayrıca raporlanır.
Başlangıç duyarlılığı ve fading memory ölçülür.

## 5. P3 — Nonlinearlik ve bellek bölgesi, 0 FC

Her platform ve mimaride 256 deterministik Sobol noktası; kaynaklı sınırlar ve
tasarım ilk skordan önce kilitli. Fiziksel olarak birlikte mümkün kayıp/kuplaj/Kerr,
detuning, güç, sembol süresi; iki halkada rezonans farkı ve karşılıklı kuplaj aranır.
Geometriyle bağlı değerler bağımsız serbest sayılar değildir. P1 ilişkileri P4 ile daraltılır.

Geçiş:
- Beş seed medyanı <0.04 ve en az 4/5 seed <0.05.
- Aynı çalışma noktasında Kerr-off medyanına göre en az %10 göreli NMSE iyileşmesi.
- Yeniden optimize edilmiş lineer kontrol ayrıca raporlanır; ablation tek başına üstünlük değildir.
- Zaman çözümü sıkılaşınca NMSE değişimi <%1.

Güçlü optik nonlinearlık bu kapıların yerine geçmez.

## 6. P4 — Angler ile halka geometrisi, yerel 0 FC

Önce FEMwell kesit modu, grup indisi ve nonlinear örtüşme; sonra Angler 2B etkin model.
2B kaynak genliği çip mW değeri değildir. Güç/enerji ve etkin nonlinear katsayı
kesit alanlarından türetilir; Angler ile zaman modeli katsayı dönüşümü belgelenir.
2B sonuç tasarım aracıdır, nihai geometrik kanıt değildir.

Serbestlik: yarıçap, genişlik, bus-ring/ring-ring gap, kuplaj uzunluğu ve düzgün
sınırlı genişlik değişimleri. Halka sürekliliği korunur; adacık/piksel yok.
Minimum özellik/eğrilik sınırı P1 proses kaynaklarından gelir.
Önce parametrik tarama; adjoint varsa tasarım değişkeni gradyanı sonlu farkla doğrulanır.

Hedef tek nokta alan şiddeti değil, P3 güç/detuning bölgesindeki nonlinear
spektral cevaba yaklaşırken iletim/kayıp/toleransı korumaktır.
Geometri → EM parametreleri → zaman modeli → geliştirme skoru döngüsü kurulur.
Frekans çözümünün dinamik kararlılığı ayrıca sınanır.
Ceviche yalnız parametrik kuplaj yetersizliğinde kısıtlı bağlantı tasarımına eklenir.
Angler–Ceviche uyuşması bağımsız 3B doğrulama sayılmaz.

## 7. P5 — Geometriye bağlı dayanıklılık, 0 FC

64 ön kayıtlı senaryo: genişlik/kalınlık/gap/rezonans, kayıp/Kerr,
lazer detuning/güç ve ölçüm koşulları. Ortak proses sapması ile halka başına
farklılık ayrılır. Dağılım bilinmiyorsa senaryo kapsamı denir.

Geçiş: senaryoların en az %90'ında (64 içinde en az 58) beş-seed medyan <0.05.
Geçmezse ücretli final yok. RONN'dan aktarılan fikir/kod kaynağı belgelenir;
fiziksel ağ geliştirmede seçilip sabitlenir, kör aşamada tuning olmaz.

## 8. P6 — 3B EM ve nihai görev

Önce nominal kuplaj hücresi, sonra halka/bağlı-halka doğrulanır.
Kompleks modal portlar, radyasyon ve gerekli zaman probları kaydedilir.
Spektrum ve dinamik tahmin koşudan önce hash ile kilitlenir.

Başlangıç eşikleri: enerji artığı <1e-3; linewidth farkı <%5; rezonans farkı
<0.1 linewidth; port güç mutlak hatası <0.02.
3B alanlardan nonlinear örtüşme/enerji kontrol edilir. Lineer 3B sonuç nonlinear
kanıt değildir: doğrudan Kerr karşılaştırması veya geçerliliği gösterilmiş
pertürbatif integral gerekir; yoksa nonlinear geometri kapısı açıktır.
EM sonrası geliştirme ve dayanıklılık yeniden geçmelidir.

Ardından kaynak/kod/ortam/geometri/optik veri/maske/başlangıç/readout içerikleri
kilitlenir ve ortak kör suite bir kez değerlendirilir. Kör sonuçtan sonra tuning yok.

## 9. Arayüzler ve tekrar üretim

1. Platform kanıt paketi: kaynaklı malzeme/proses, birim/aralık, dönüşüm, içerik hash'i.
2. Geometri-model paketi: geometri, solver/grid, kompleks portlar, kayıp ayrımı,
   modal integraller ve geçerlilik bölgesi.
3. Görev adayı: dinamik model, bağımlılıklar, fizik verisi, giriş/readout, benchmark kimliği.

Parametre statüleri synthetic / source-supported / EM-supported / unresolved.
Statü etiketi tek başına kabul değildir; ilgili kapı kanıtı gerekir.
Eksikler sessiz varsayılanlarla doldurulmaz.
Angler/FEMwell/Ceviche ortamları benchmarktan izole; commit ve sürümler kilitli.
Araç uyumluluğu/örnek tekrar üretimi geçmeden büyük tarama yok.

Hedef çalışma alanı studies/plan2-kerr/; deney kimliği plan2-kerr-Pn-####.
İlk teslimatlar bu klasörde README.md, BENCHMARK-PROTOCOL.md ve PLATFORM-EVIDENCE.md.
Kod Claude tarafından mevcut tcmt/ ve fdtd/ katmanlarıyla uyumlu geliştirilecek;
ortak benchmark/ledger kopyalanarak yeni kör erişim yolu oluşturulmayacak.
Hedef yollar henüz uygulama dosyalarının varlığı anlamına gelmez.

## 10. Test, bütçe, durma

Testler: analitik halka, serbest sönüm, sıfır giriş/kuplaj, pasif denge,
karşılıklılık, Kerr sıfır limiti, sabit girişte zaman/frekans karşılaştırması,
farklı başlangıçlarda nonlinear kararlılık, mesh/domain/PML/time yakınsaması,
adjoint-sonlu fark, kilitli scorer, transitif değişim, yarış ve çökme kurtarma.
İteratif yakınsama fiziksel kararlılıkla eşdeğer değildir.

P0–P5 0 FC; duvar saati/bellek raporlanır. Kayıtlı 115.7358 FC canlı bakiye
değildir; diğer taahhütlerle birlikte yenilenir. Her hatta ayrı 47 FC yoktur.
60 FC taban, 25 FC tek koşu, ortak 20 FC final rezerv korunur.
Her solve yazılı estimate ve Hasan onayı ister; B25 tarihsel eşik kararı çözülmeden
yeni ücretli solve yok. P6 sayısı ve maliyeti kanıt ihtiyacından sonra belirlenir.

Durma: kaynaklı güçte görev avantajı yok; 2B–3B normalizasyon yok; gerçek dışı
parametreyle kazanç; dayanıklılık başarısız; 3B kanıt bütçeye sığmıyor.
İlk teslimat P0 sözleşmesi + P1 kaynak/fizibilite tablosu + P2 analitik testli
çekirdektir. Bunlar görülmeden Angler tasarım taraması başlamaz.

## Araştırma hattı bağlantıları

- [[docs/PROJECT-CHARTER|Proje üst sözleşmesi]]
- [[docs/decisions/2026-09-14-recovery-implementation-contract|Ortak benchmark güvenliği ve bütçe kapısı]]
- [[docs/decisions/2026-09-13-optical-chain-recovery-plan|Ayrı silikon kurtarma hattı]]
