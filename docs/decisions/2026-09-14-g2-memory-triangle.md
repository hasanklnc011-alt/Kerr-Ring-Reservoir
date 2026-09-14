# G2 — Kerr bellek üçgeni tamamlandı

- Durum: KAPALI (tarama yapıldı ve test edildi), 2026-09-14.
- Sahip: Claude (kod/test).
- Rapor: [studies/plan2-kerr/MEMORY-TRIANGLE.md](../../studies/plan2-kerr/MEMORY-TRIANGLE.md)
- Üst karar: [proje sözleşmesi](../PROJECT-CHARTER.md) §Ön kapılar,
  [Plan 2 ADR](2026-09-14-plan2-kerr-reservoir.md).

## Bulgu

Kerr anlık olduğu için Kerr-only halkada bellek yalnız kavite sönümünden
gelir. Bu, görev derinliği `m`, mask slot sayısı `N`, sürücü bant genişliği
`B` ve yüklü `Q_L` arasında malzemeden bağımsız bir taban doğurur:

```
Q_floor = m · ω₀ · N / ( ln(1/ε) · B )
```

Plan 2'nin nominal ayarında (`m=10`, `N=20`, `B=50 GHz`, `ε=1/e`, 1550 nm):

- `Q_floor = 4.86 × 10⁶` (yüklü), kritik kuplajda `Q_i = 9.72 × 10⁶`.
- `n_g = 2.0` için bu **0.036 dB/cm**'lik bir kayıp bütçesi demektir.
- Si₃N₄ (0.1 dB/cm çalışma figürü) ve AlGaAsOI (kaynaklı `Q_i = 3.52 × 10⁶`)
  adaylarının ikisi de bu tabanın altında kalıyor: **nominal ayarda
  fizibilite bölgesi boş.**
- Her iki adayın taşıyabildiği: ~7 slot, ya da 138 GHz sürücü, ya da
  ~3.6 sembol derinlik.

## Kararı değiştiren şey

Darboğaz nonlinearite değil, **bellek**; ve platform seçimi belleği satın
alamaz. `n₂` yalnız izin verilen güçte yeterli kaymanın alınıp alınmadığını
belirler. Bu, "AlGaAsOI yüksek `n₂` sunuyor" argümanının G2 düzeyinde
belirleyici olmadığını gösterir.

İkinci bulgu: `ρ_Kerr ∝ Q²` olduğundan bellek ve nonlinearite aynı yöne
çekiyor — bu mimaride klasik bellek/nonlinearite gerilimi yok. Gerçek
gerilim `F²R ∝ 1/R`: kayıp bütçesi büyük halka, Kerr küçük halka istiyor.
Bu, P4'ün asıl tasarım sorusudur.

## Açık bırakılan

`ε` (10 sembol sonra hayatta kalması gereken enerji kesri) şu an bir
modelleme seçimi. Gerçek soru artığın readout gürültü tabanının üstünde
olup olmadığıdır; gürültü ve ADC çözünürlüğü modellenmeden taban keyfîdir.
**G2'nin en zayıf halkası budur ve P2'de kapatılmalıdır.**

Termal kayma hesaplanamadı: soğurulan kayıp kesri ve termal direnç yok.
Kod tahmin üretmiyor, `None` döndürüyor. P1/K2a işi.

## Sıradaki adımın çerçevesi (karar Hasan'ın)

Bölge prensipte boş değil. Açmanın üç yolu raporda sayıyla listelendi:
slot sayısını düşürmek (en güçlü ve en ucuz kaldıraç), bant genişliğini
artırmak (erişilebilirlik kuralına çarpar), `ε`'u gerekçelendirmek.
Dördüncü bir yol Plan 2'nin kapsamı dışındadır: belleği kaviteden değil
açık bir gecikme hattından almak.

Bu ADR bu seçeneklerden hiçbirini benimsemez.

## Kanıt

- `plan2_kerr/memory_triangle.py`, `platforms.py`, `screen.py`.
- `tests/plan2_kerr/` 41/41 geçiyor: birim dönüşümleri, taban-tutma
  tutarlılığı (tabandaki kavite tam olarak `ε` tutuyor), ölçekleme yasaları
  (`m`, `N`, `T_sym`, `B`, `ε`, `Q²`, `1/R`), finesse'in iki yoldan aynı
  çıkması, güç↔kayma tersliği, sınır fonksiyonlarının tabanı tersine
  çevirmesi, termalin eksik girdide `None` dönmesi, parametre statüsü
  denetimi ve nominal sonucun regresyon sabitlenmesi.
- Üretim komutu: `python -m plan2_kerr.screen --boundary`.

## Kapsam dışı

Fiziksel kabul değildir. P1 kaynak tablosunu ikame etmez. Tek halka, tek
mod, kritik kuplaj ve rezonansta çalışma varsayıldı; iki bağlı halka ayrı
bir tabandır ve hesaplanmadı.
