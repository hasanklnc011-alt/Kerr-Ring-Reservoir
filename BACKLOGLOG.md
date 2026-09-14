# Backlog geçmişi

Kapanan iş kalemlerinin kanıt ve commit izleri buraya yazılır.

## [G0] Kör-test güvenliği — CLOSED 2026-09-14

Devralınan üç kusur canlı kodda doğrulandı ve kapatıldı: blind-eval baseline
çağırıyordu, tüketim skordan sonra yazılıyordu, CLI kilitli ayarları geçersiz
kılabiliyordu. Kilit v2, atomik rezervasyon defteri, süreç kilidi ve
checkpoint'li kurtarma eklendi. Testler 82 → 122.

Karar: docs/decisions/2026-09-14-g0-blind-test-safety.md

## [G2] Kerr bellek üçgeni — CLOSED 2026-09-14

Kerr-only halkada belleğin yalnız kavite sönümünden geldiği gözleminden
malzemeden bağımsız bir Q tabanı türetildi. Plan 2'nin nominal 20-slot /
50 GHz ayarında bölge iki aday platformda da boş çıktı; darboğazın
nonlinearite değil bellek olduğu ve platform seçiminin belleği satın
alamadığı gösterildi. 41 test eklendi.

Karar: docs/decisions/2026-09-14-g2-memory-triangle.md
Rapor: studies/plan2-kerr/MEMORY-TRIANGLE.md
