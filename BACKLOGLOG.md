# Backlog geçmişi

Kapanan iş kalemlerinin kanıt ve commit izleri buraya yazılır.

## [G0] Kör-test güvenliği — CLOSED 2026-09-14

Devralınan üç kusur canlı kodda doğrulandı ve kapatıldı: blind-eval baseline
çağırıyordu, tüketim skordan sonra yazılıyordu, CLI kilitli ayarları geçersiz
kılabiliyordu. Kilit v2, atomik rezervasyon defteri, süreç kilidi ve
checkpoint'li kurtarma eklendi. Testler 82 → 122.

Karar: docs/decisions/2026-09-14-g0-blind-test-safety.md
