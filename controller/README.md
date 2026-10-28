# Kontrol yazılımı

Platformu döndüren, atığı bırakan, bırakmayı doğrulayan ve bölmelerin doluluğunu ölçen durum makinesi.

```
IDLE → ROUTING → DROPPING → VERIFYING → RETURNING → IDLE
          └──────────┴───────────┴───────────┴──→ FAULT (güvenli durdurma)
```

| Durum | Ne olur | Arıza kodu |
|---|---|---|
| ROUTING | Step motor platformu hedef bölmenin açısına döndürür | `position_error` |
| DROPPING | Servo kapağı açar, atığın platformdan ayrılması beklenir | — |
| VERIFYING | Kızılötesi sensör atığın gittiğini doğrular | `jam` |
| RETURNING | Platform referans sensörüne geri döner | `home_error` |

Arızada kapak kapatılır, motor durdurulur ve `reset()` çağrılana kadar yeni ayırma kabul edilmez.

## Dosyalar

- `hardware.py`: Donanım arayüzleri (Platform, Gate, PresenceSensor, DistanceSensor), bölme açıları, mesafe → doluluk dönüşümü
- `state_machine.py`: `SortController`
- `simulated.py`: Donanımsız çalışan sürücüler; `world.faults` ile arıza denenebilir (`jam`, `position`, `home`)

Raspberry Pi sürücüleri aynı arayüzleri uygulayacak; durum makinesi değişmeyecek.

Sürücü ve sensör çağrıları süreyle sınırlıdır. Zaman aşımı Python iş parçacığını
sonlandırmaz: devam eden çağrı izlenir ve bitmeden sıfırlama kabul edilmez.
Gerçek motor sürücüsünün `stop()` komutu devam eden hareketi iptal etmeli;
sensör sürücüleri de kendi I/O zaman aşımını uygulamalıdır. Yazılımın süre sınırı
fiziksel acil durdurmanın yerini tutmaz.
