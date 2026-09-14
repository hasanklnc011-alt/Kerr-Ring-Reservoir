# Plan 2 hattının ayrı depoya taşınması

- Durum: KABUL EDİLDİ (Hasan, 2026-09-14).
- Kaynak depo: `hasanklnc011-alt/Nonlinear-3D-FDTD-Photonic-Reservoir`
- Yeni depo: bu depo.

## Karar

Plan 2 Kerr hattı ayrı bir yerel klasör ve ayrı bir GitHub deposunda yürütülür.
Silikon kurtarma hattı (K0–K5) kaynak depoda kalır. İki hat ayrı depolarda
olmakla **ayrı bütçe, ayrı rezerv veya ayrı kör-suite hakkı kazanmaz**.

## Devralınanlar

| İçerik | Yol | Statü |
|---|---|---|
| NARMA-10 benchmark kodu ve testleri | `benchmarks/`, `tests/narma10_np/` | Taşındı; benchmark kimliği ve sabitler değişmedi |
| Dev/kör seed hash manifestleri | `manifests/narma10/` | Taşındı; 200/3000/2000 split ve hash'ler korundu |
| FlexCredit defteri ve B25 | `reports/FLEXCREDIT-LEDGER.md` | Devralındı; bütçe ortak, B25 OPEN |
| Optik parametre geri çekme raporu | `docs/inherited/OPTICAL-PARAMETER-STATUS.md` | Tarihçe; talimat değil |
| Çürütme/ön kayıt ADR'leri | `docs/inherited/` | Tarihçe; bu depoda yeniden kabul edilmedi |

`docs/inherited/` altındaki hiçbir belge bu depoda geçerli bir kabul veya
talimat değildir. Oradaki optik parametrelerin tamamı geri çekilmiştir.

## Kör suite — tek erişim yolu

Kör suite **taşınmıştır, kopyalanmamıştır**. 10 kör seed'in tek meşru
değerlendirme yolu bu depodur. Kaynak depoda kör değerlendirme yolu kapatılır
ve bu karara işaret eden bir kayıt bırakılır.

Kör suite tek nihai aday üzerinde bir kez tüketilir. Farklı aday kimliği,
farklı hat veya farklı depo suite'i yeniden açamaz.

## Devralınan açık bug (G0)

Kaynak depodaki K2s kaydına göre kör değerlendirme yolunda üç kusur vardır:
guard kalıcı tüketim yapmıyor, kayıt skor sonrasında yazılıyor ve blind-eval
gerçek scorer yerine baseline çağırıyor. Bu kod olduğu gibi devralındı;
kusurlar bu depoda G0 olarak açıktır. **G0 kapanmadan gerçek kör
değerlendirme çalıştırılmaz**; regresyonlar geçici sentetik suite kullanır.

## Kapsam dışı

Eski silikon geometri kısıtları (450×220 nm, R=4.775 µm, 150–250 nm gap),
K0–K5 iş kalemleri ve eski FDTD ham verisi bu depoya taşınmadı.
