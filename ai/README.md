# Yapay zekâ modülü

Atıkları dört sınıfa ayıran YOLOv8 sınıflandırma modeli: **cam, metal, kâğıt, plastik**.

## Yaklaşım

- **Model:** `yolov8n-cls`. ImageNet üzerinde önceden eğitilmiş ağırlıklardan aktarım öğrenmesiyle eğitilir.
  Platformda aynı anda tek atık bulunduğu için konum kutusuna gerek yoktur; sınıflandırma yeterlidir.
- **Hazır veri seti:** [TrashNet](https://huggingface.co/datasets/garythung/trashnet) (küçültülmüş sürüm).
  Sade zemin üzerinde tek atık; platform düzenimize benzer. Karton → kâğıt, "trash" sınıfı kullanılmaz.
- **Kendi veri setimiz:** Platform kamerasıyla çekilen görüntüler aynı klasör yapısında toplanacak;
  hazır veriyle eğitilen ve kendi verimizle ince ayar yapılan modeller karşılaştırılacak.

## Tekrarlanabilir bölünme

Train/val/test bölünmesi `splits/trashnet-v1.csv` dosyasında saklanır ve git'e eklenir.
`prepare_trashnet.py` bu dosya varsa bölünmeyi oradan okur; böylece her bilgisayarda aynı test
kümesi oluşur ve farklı modeller aynı görüntülerde karşılaştırılabilir. İlk modelin (best-c48b4813)
sonuçları bu bölünmeye aittir.

## Bilinen sınırlar

- **Güven eşiği tek başına yeterli değil.** Testteki 27 yanlış tahminin 24'ü 0,6 eşiğini geçiyor;
  sistemin ayıracağı atıklarda hata oranı ~%6,7. `evaluate.py` bu sayıyı ayrıca raporlar.
- **Kapalı küme.** Model her görüntüyü dört sınıftan birine atar. Boş platform ya da kapsam dışı
  nesneler için yüksek güvenli yanlış sonuç verebilir (ör. kameranın test deseni %71 "kâğıt"
  olarak sınıflandı). Boş platform ve "diğer" görüntüleri kendi veri setine eklenmeli.
- **TrashNet ≠ bizim platform.** Test başarısı, gerçek platformdaki başarıyı göstermez.

## Kurulum

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Kullanım

```bash
.venv/bin/python prepare_trashnet.py   # veri setini indir ve böl (70/15/15)
.venv/bin/python train.py              # eğit → weights/best.pt
.venv/bin/python evaluate.py           # test kümesinde değerlendir → reports/
```

`weights/best.pt` oluştuğunda backend bu modeli kendiliğinden kullanır.

## Kendi veri setini ekleme

Aynı fiziksel nesnenin birbirine çok benzeyen kareleri eğitim ve teste dağıtılmamalı; aksi halde
test sonucu olduğundan iyi çıkar. Dosya adına nesne numarası yazıp (ör. `plastic_n012_03.jpg`)
bölmeyi nesne bazında yap.

```
datasets/kendi/
├── train/{glass,metal,paper,plastic}/*.jpg
├── val/...
└── test/...
```

```bash
.venv/bin/python train.py --data datasets/kendi --model weights/best.pt --name ince-ayar
.venv/bin/python evaluate.py --data datasets/kendi/test
```

Veri setleri, eğitim çıktıları (`runs/`) ve ağırlıklar (`*.pt`) git'e eklenmez.
