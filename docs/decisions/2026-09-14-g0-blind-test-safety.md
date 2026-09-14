# G0 — kör-test güvenliği kapatıldı

- Durum: KAPALI (uygulandı ve test edildi), 2026-09-14.
- Sahip: Claude (kod/test).
- Üst karar: [migrasyon](2026-09-14-repo-migration.md), [Plan 2 ADR](2026-09-14-plan2-kerr-reservoir.md).

## Devralınan kusurlar

Eski depodan olduğu gibi devralınan üç kusur canlı kodda doğrulandı:

1. `cmd_blind_eval` kilitli adayı değil `baseline_delay_scorer`'ı çalıştırıyordu.
   Yani tek kör deneme, bilinen ve hedefin çok üstünde olan lineer kontrol
   üzerinde tüketilirdi.
2. Tüketim skordan **sonra** yazılıyordu. Koşu ortasında çöken bir süreç
   defterde iz bırakmıyordu; kör sete ikinci bakış ücretsiz oluyordu.
3. CLI kilitli ayarları geçersiz kılabiliyordu: `blind-eval --n-delays --alpha`.

Ayrıca v1 kilidi tek bir dosyayı donduruyor ve çalışacak scorer'ı hiç
adlandırmıyordu; transitif olarak import edilen bir yardımcı kilit sonrası
değişse yakalanmıyordu.

## Uygulanan sözleşme

**Kilit v2 (`narma10-candidate-lock/2`).** Tek dosya değil, paket dondurulur:

- `entry_point` — `"modül:fabrika"`, scorer'ı döndüren sıfır argümanlı fabrika.
- `sources` — `source_root` altındaki **her** dosyanın içerik hash'i. Değişen,
  silinen ve kilit sonrası **eklenen** dosya ayrı ayrı yakalanır.
- `readout` — slot, port, özellik sayısı, örnekleme noktası, dijital tap sayısı
  (sıfır olmak zorunda) ve ridge seçim protokolü.
- Ortam bloğu (Python, platform, NumPy) ve iki manifest digest'i.

v1 kilitleri gerçek kör değerlendirmeye **kabul edilmez**; `load_lock` şemayı
reddeder.

**Baseline yasağı.** `BANNED_ENTRY_POINTS` baseline'ı kilit anında, guard
anında ve import anında reddeder. Import anındaki kontrol çözülmüş
`__module__:__qualname__` üzerinden yapıldığı için baseline'ı başka bir isimle
yeniden dışa aktarmak da geçmez.

**Tüketim skordan önce (`narma10-blind-ledger/2`).** Sıra:
guard (salt-okunur) → dışlayıcı süreç kilidi → `reserve_attempt` → kilitli
scorer → `complete_attempt`. Defter yazımları geçici dosya + `os.replace` ile
atomiktir. Çöken koşu defterde `reserved` bırakır; sıfırdan yeni deneme
reddedilir.

**Eşzamanlılık.** `O_CREAT | O_EXCL` ile açılan süreç kilidi; ikinci koşu
`BlindEvaluationBlocked` alır ve deftere hiç dokunmaz.

**Kurtarma.** Yalnız `--resume-run <run_id>` ile: aynı aday, aynı `run_id`,
aynı kilit içerik digest'i, aynı kör manifest digest'i ve bu dördüyle uyuşan
bir checkpoint. Uyuşmayan checkpoint yok sayılmaz, hata verir. Deftere el ile
dokunup "yeniden denemek" kurtarma değil, sözleşme ihlalidir.

**Tek kullanım.** Tamamlanmış bir deneme varken farklı aday kimliğiyle suite
yeniden açılamaz; hata mesajı bunu açıkça söyler.

**CLI kilitli ayarı değiştiremez.** `blind-eval` yalnız `--id` ve
`--resume-run` alır. Skorlama parametresi kalmadı.

## Kanıt

`tests/narma10_np/` 122/122 geçiyor (önce 82). Yeni testler:

- `test_candidate_lock.py` — kaynak sürüklenmesi (değişen/silinen/eklenen
  dosya), transitif yardımcı değişimi, v1 kilidinin reddi, baseline ve
  baseline-alias'ının reddi, readout sözleşmesi, entry point hataları.
- `test_blind_candidate_execution.py` — scorer patlasa bile denemenin tüketilmiş
  olması, ikinci rezervasyonun bloke olması, farklı aday kimliğiyle suite'in
  yeniden açılamaması, kilitli scorer'ın baseline'dan farklı skor vermesi,
  süreç kilidi yarışı, checkpoint'ten kurtarma ve yabancı checkpoint/`run_id`
  reddi, defter şema/bozulma kontrolleri, atomik yazım.

`python -m benchmarks.narma10_np preflight` 8/8 PASS/INFO.

## Kapsam dışı

Gerçek bir aday henüz yok; kör suite tüketilmedi ve defter boş. Bu kapı yalnız
yolun güvenliğini kapatır, fizik hakkında hiçbir şey söylemez.
