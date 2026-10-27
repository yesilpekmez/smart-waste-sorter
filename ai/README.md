# Yapay zekâ modülü

Atıkları dört sınıfa ayıran YOLOv8 sınıflandırma modeli: **cam, metal, kâğıt, plastik**.

## Yaklaşım

- **Model:** `yolov8n-cls`. ImageNet üzerinde önceden eğitilmiş ağırlıklardan aktarım öğrenmesiyle eğitilir.
  Platformda aynı anda tek atık bulunduğu için konum kutusuna gerek yoktur; sınıflandırma yeterlidir.
- **Hazır veri seti:** [TrashNet](https://huggingface.co/datasets/garythung/trashnet) (küçültülmüş sürüm).
  Sade zemin üzerinde tek atık; platform düzenimize benzer. Karton → kâğıt, "trash" sınıfı kullanılmaz.
- **Kendi veri setimiz:** Platform kamerasıyla çekilen görüntüler aynı klasör yapısında toplanacak;
  hazır veriyle eğitilen ve kendi verimizle ince ayar yapılan modeller karşılaştırılacak.

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
