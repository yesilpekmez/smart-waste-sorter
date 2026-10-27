# Akıllı Atık Ayırma Sistemi

Görüntü işleme ve doluluk takibi ile cam, metal, plastik ve kâğıt atıklarını ayıran sistem.

```
Kamera → YOLOv8 (ai/) → Flask API (backend/) → Kontrol durum makinesi (controller/) → Motorlar ve sensörler
                              ↕
                     React paneli (frontend/)
```

## Durum

| Bölüm | Durum |
|---|---|
| Yapay zekâ | YOLOv8n-cls, TrashNet ile eğitildi: test doğruluğu %92,5, makro F1 0,913 |
| Backend | Algılama, ayırma, doluluk, işlem geçmişi ve istatistik API'si |
| Kontrol yazılımı | Durum makinesi ve güvenli durdurma; simüle donanımla çalışıyor |
| Panel | Canlı görünüm, sınıflandırma, doluluk, arıza yönetimi, işlem geçmişi |
| Donanım | Raspberry Pi sürücüleri ve montaj: sırada |

## Klasörler

| Klasör        | İçerik                                         |
|---------------|------------------------------------------------|
| `ai/`         | Veri seti hazırlama, model eğitimi ve değerlendirme |
| `backend/`    | Flask REST API ve SQLite veritabanı            |
| `frontend/`   | React + TypeScript kontrol paneli              |
| `controller/` | Ayırma durum makinesi ve donanım arayüzleri    |
| `hardware/`   | Raspberry Pi bağlantı şemaları, GPIO kodu      |
| `tests/`      | Backend ve kontrol yazılımı testleri           |
| `docs/`       | Rapor ve şemalar                               |

## Çalıştırma

```bash
# 1. Model (bir kez): ai/README.md
cd ai && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python prepare_trashnet.py && .venv/bin/python train.py

# 2. Backend: http://localhost:5000
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py

# 3. Panel: http://localhost:5173
cd frontend && npm install && npm run dev
```

`ai/weights/best.pt` yoksa backend örnek sınıflandırıcıyla çalışır.

## Testler

```bash
backend/.venv/bin/python -m pytest tests
```

## API

| Uç nokta | Açıklama |
|---|---|
| `POST /api/detect` | Fotoğrafı sınıflandırır (`image` alanı, multipart) |
| `POST /api/sort` | `{detectionId}`: kuralları uygular, ayırmayı başlatır |
| `GET /api/bins` | Bölmelerin doluluğu (sensörlerden) |
| `GET /api/system`, `POST /api/system/reset` | Kontrol servisinin durumu, arızadan sonra sıfırlama |
| `GET /api/operations` | İşlem geçmişi (`label`, `status`, `limit`, `offset`) |
| `GET /api/stats` | Başarı oranı, ortalama güven, sınıf bazında sayılar |
