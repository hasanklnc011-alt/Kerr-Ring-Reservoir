> Güncel geçerlilik: [Kurtarma ADR](2026-09-13-optical-chain-recovery-plan.md).
> Aşağıdaki tarihsel iddialar güncel parametre kabulü yerine kullanılamaz.

# 2026-09-13 — ADR: TCMT birincil çözücü, FDTD optik parametrelerin yetkili kaynağı

- Karar sahibi: Hasan (açık onay)
- Yazan: Claude Opus 5
- Durum: KABUL EDİLDİ — yürürlükte
- Değiştirdiği: `const.md` §Bilimsel sözleşme, `AGENTS.md` §Amaç / §Aşamalar / §Kanıt kuralları
- Çözdüğü blokaj: `docs/coordination/2026-09-13-claude-review-of-tcmt-fdtd-plan.md` R4

## Karar

`const.md`'nin "nihai elektromanyetik çözüm Tidy3D ile uçtan uca 3D FDTD
olmalıdır" ve "TCMT/reduced-order sonuçları yardımcı kanıttır; full 3D FDTD
yerine geçmez" hükümleri kaldırıldı. Yerine iki rollü bir kanıt sözleşmesi kondu:

- **FDTD/eigenmode — optik parametrelerin tek yetkili kaynağı.** `Q_i`, `Q_e`,
  bus-ring coupling, rezonans, `n_eff`, mode volume ve nonlinear overlap
  integralleri yalnızca full-wave ölçümünden gelir. Bu büyüklükler serbest
  parametre olarak seçilemez, deneye fit edilemez, literatürden kopyalanamaz.
- **TCMT/rate-equation — zaman-serisi görev çözücüsü.** NARMA-10 dizisi bu
  modelle çözülür; girdileri yukarıdaki FDTD ölçümleriyle ve kaynak-hash'li
  malzeme/carrier/termal parametreleriyle sınırlıdır.

## Bu neden "rollerin takası" değil

Eski sözleşmede TCMT "yardımcı kanıt"tı. Yeni sözleşmede FDTD **yardımcı kanıt
değildir** — daha katı bir role geçmiştir: TCMT'nin girdilerini *kilitleyen*
merci. Eski kurguda TCMT parametreleri prensipte serbestti ve FDTD onları
yalnız destekliyordu; yeni kurguda TCMT hiçbir optik parametreyi kendi
seçemez. Kanıt yükü azalmadı, yer değiştirdi ve arttı.

## Gerekçe — eski hüküm ulaşılamazdı

İki bağımsız, belgelenmiş bulgu:

1. **CFL duvarı.** NARMA-10 dizisini uçtan uca femtosaniye Maxwell adımlarıyla
   çözmek gerekiyordu. Zaman adımını gevşetecek yayınlanmış yöntemlerin
   (ADI+ADE, Faber polinomları, zarf-Maxwell, precise-integration) **hiçbiri**
   Tidy3D'nin kapalı explicit Yee çözücüsüne eklenemiyor. Tidy3D'yi bırakmadan
   aşılamaz. (`reports/FDTD-001-mrr-feasibility.md`)
2. **FCD/FCA ve termal ODE'ler native değil.** Altı bağımsız kaynağa göre
   silicon MRR reservoir'de asıl bellek mekanizması serbest taşıyıcı +
   termo-optik etkileşimdir; bunlar ns–µs ölçeğinde çalışır ve Tidy3D'nin
   fs-adımlı zaman eksenine self-consistent bağlanamaz.
   (`reports/FDTD-001-mrr-feasibility.md`, "FCD/FCA riski — YÜKSEK")

Yani `const.md` yapılamayacak bir şeyi zorunlu kılıyordu ve bu plan altında
atılan her adım nominal olarak sözleşmeyi ihlal ediyordu.

## Gerekçe — yeni rol ölçümle desteklendi

Karar teorik değil. 2026-09-13'te FDTD'nin optik parametre üretebildiği fiilen
gösterildi (`docs/decisions/2026-09-13-freq-rung-2-evaluation.md`):

```
lambda_0     = 1.540945 um
Q_loaded     =  9 797          (iki port bagimsiz, %0.6 icinde)
Q_e (toplam) = 12 260          Q_c = 24 519
x            = 0.799  -> belirgin OVER-coupled
n_eff        = 2.4017          cekirdek guc %60-63   (mode solver, 0 FC)
```

Üç observability kusuru bulunup kapatıldıktan sonra (frekans tarağı, port
yerleşimi, facet sonlandırması) enerji dengesi rezonans dışında `1.0000`'a
`2e-4` yakınlıkta kapandı. Yani FDTD'nin bu rolü üstlenebileceği kanıtlandı.

## Değişmeyenler

Bu ADR **yalnız** elektromanyetik çözüm mimarisini değiştirir. Şunlara
dokunmaz:

- Nihai görev NARMA-10;
- Kabul hedefi 10 kör seed üzerinde medyan test NMSE `< 0.05`;
- Kör test sonucunun tuning'e geri beslenememesi;
- Ücretli solve öncesi maliyet raporu ve Hasan onayı;
- Provenance/hash kilidi ve fail-closed doğrulama.

## Kabul edilen bedel — iddia kapsamı daralıyor

Bu değişiklikle **uçtan uca Maxwell kanıtından vazgeçiyoruz**. Sonuç
yayınlanırsa iddia "full-wave photonic reservoir" değil, **"geometriyle
sınırlandırılmış, FDTD-kalibre edilmiş TCMT reservoir"** olmalıdır. Bu sınır
`const.md`'ye yazıldı ki ileride fazla iddia edilmesin.

Ayrıca: TCMT'nin kendi doğruluğu artık bir risk kalemidir. Model, ölçülmüş
optik parametrelerle sınırlı olsa bile, mod sayısı ve nonlinear terimleri
eksikse yanlış sonuç verebilir. Bunun karşı önlemi C2 mekanizma
ablation'larıdır ve plan incelemesindeki R1 (iki modlu CW/CCW port
sözleşmesi) bu ADR'nin ön şartı olarak kalır.

## Sonraki adım

R4 çözüldüğüne göre WP1 (literatür + model sözleşmesi) başlatılabilir.
Kalan revizyonlar R1, R2, R3, R5, R6 taslağın içinde çözülmelidir;
`docs/coordination/2026-09-13-claude-review-of-tcmt-fdtd-plan.md`.
