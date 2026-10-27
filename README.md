# Akıllı Atık Ayırma Sistemi

Görüntü işleme ve doluluk takibi ile cam, metal, plastik ve kâğıt atıklarını ayıran sistem.

## Klasörler

| Klasör        | İçerik                                         |
|---------------|------------------------------------------------|
| `ai/`         | YOLOv8 model eğitimi ve tahmin                 |
| `backend/`    | Flask REST API ve veritabanı                   |
| `frontend/`   | React + TypeScript kontrol paneli              |
| `controller/` | Kontrol durum makinesi (motor, sensör mantığı) |
| `hardware/`   | Raspberry Pi bağlantı şemaları, GPIO kodu      |
| `tests/`      | Testler                                        |
| `docs/`       | Rapor ve şemalar                               |

## Frontend'i çalıştırma

```bash
cd frontend
npm install
npm run dev
```
