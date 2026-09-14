# Proje sabitleri

Bu dosya değişmez kabul edilen gerçekleri ve sözleşmeleri içerir. Bir karar
bunlardan birini değiştirecekse önce `docs/decisions/` altında açık bir karar
kaydı oluşturulmalıdır.

## Kimlik ve konum

- Proje adı: Kerr Ring Reservoir
- Yerel kök: `C:\Users\hasan\OneDrive\Desktop\Kerr-Ring-Reservoir`
- Uzak depo: (ilk push'ta doldurulacak)
- Kaynak depo: `https://github.com/hasanklnc011-alt/Nonlinear-3D-FDTD-Photonic-Reservoir.git`
- Kod/test sahibi Claude; Codex yalnız plan, sözleşme ve değerlendirme dokümantasyonu.

## Bilimsel sözleşme

- **Araştırma sorusu:** Halka geometrisini ve kuplajını tasarlayarak erişilebilir
  optik güçte görev açısından yararlı nonlinearlık ve zamansal bellek elde
  edilebilir mi?
- **Geometriye bağlı optik parametreler EM kanıtıyla sınırlandırılır.** Kuplaj,
  rezonans, mod profili ve overlap EM'den gelir. Malzeme, absorpsiyon, carrier
  ve termal girdiler kaynaklandırılır. Bilinmeyenler NMSE'ye uydurulmaz.
- **Görev çözücüsü zaman-alanı TCMT/rate-equation modelidir.**
- **Nonlinearlik ≠ bellek.** Kerr anlıktır; bellek kavite ömrü ve/veya eklenen
  yavaş dinamiklerden gelir. Her aday için bellek mekanizması açıkça yazılır.
- **Kerr-only fiziksel kabul vermez.** Platformun anlamlı nonlinear absorpsiyonu
  ve termal kayması modele girmeden fiziksel kabul yoktur.
- Nihai görev NARMA-10'dur. Kabul: 10 kör seed medyan `< 0.05` ve en az 8/10 `< 0.05`.
- Kör test sonucu tuning'e geri beslenemez; suite bir kez tüketilir.
- **İddia kapsamı:** sonuç "full-wave photonic reservoir" değil, "EM ile
  sınırlandırılmış, kalibre edilmiş zaman-alanı reservoir modeli" olarak sunulur.

## Parametre statüleri

`synthetic` / `source-supported` / `EM-supported` / `unresolved`.
Statü etiketi tek başına kabul değildir; ilgili kapı kanıtı gerekir.
Eksikler sessiz varsayılanlarla doldurulmaz.

## Süreç sözleşmesi

- Ücretli solve öncesi yazılı estimate, canlı bakiye kontrolü ve Hasan'ın açık
  onayı zorunludur. 60 FC taban, 25 FC tek koşu tavanı, 20 FC final rezerv.
  B25 tarihsel bütçe kararı OPEN olduğu sürece yeni ücretli solve yoktur.
- Bütçe, rezerv ve kör suite eski depoyla **ortaktır**; iki hat ayrı hak kazanmaz.
- API anahtarları, ham HDF5 ve büyük artifact'ler Git'e eklenmez.
- Yarıda kalan işler `BACKLOG.md`, kapanış izleri `BACKLOGLOG.md` içine yazılır.
- `AGENTS.md` ve `CLAUDE.md` her değişiklikte birlikte güncellenir.

## Sınır

Fiziksel parametreler, platform, mimari, güç ve sembol hızı kanıt geldikçe
raporlarda belirlenir. Bunlar bu dosyanın değişmezleri değildir.
