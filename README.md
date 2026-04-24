# 📅 Masaüstü Takvim & Not Defteri

Masaüstünüzde köşede duran, şeffaf cam görünümlü, sürüklenebilir bir takvim ve not uygulaması.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## ✨ Özellikler

- 🪟 **Şeffaf & frameless** pencere — ekranı kapatmaz
- 📌 **Her zaman üstte** — diğer pencerelerin önünde durur
- 🖱️ **Sürükle-bırak** — istediğin yere taşı, konum kaydedilir
- ➖ **Küçült** — yuvarlak tarih ikonuna dönüşür, sürüklenebilir
- 📝 **Günlük notlar** — her güne başlık, açıklama, saat ekle
- 🔴 **Durum renkleri**: Yeşil = tamamlandı, Turuncu = bekliyor, Kırmızı = geçmiş
- 🔔 **Bildirim** — saati olan notlar için 15 dk önce sistem bildirimi
- ⚠️ **Geçmiş notlar** — tamamlanmamış eski notları tek ekranda gör
- 🎨 **Tema seçimi** — Mavi, Bordo, Gri, Yeşil, Turuncu
- 🏷️ **Özelleştirilebilir isim** — takvimine kendi adını ver
- 🗃️ **Yerel veritabanı** — tüm notlar bilgisayarında SQLite ile saklanır

---

## 🚀 Kurulum

### Gereksinimler
- Python 3.11 veya üstü → [python.org](https://www.python.org/downloads/)

### Adımlar

```bash
# 1. Projeyi indir
git clone https://github.com/KULLANICI_ADIN/desktop-calendar.git
cd desktop-calendar

# 2. Sanal ortam oluştur
python -m venv .venv

# 3. Bağımlılıkları yükle
.venv\Scripts\pip install -r requirements.txt

# 4. Çalıştır
.venv\Scripts\pythonw main.py
```

Veya sadece **`run.bat`** dosyasına çift tıkla — gerisini otomatik yapar.

---

## 📁 Proje Yapısı

```
desktop-calendar/
├── main.py          # Giriş noktası, sistem tepsisi
├── window.py        # Ana takvim penceresi
├── dialogs.py       # Not ekle/düzenle diyaloğu
├── database.py      # SQLite veri katmanı
├── notifier.py      # Bildirim zamanlayıcısı
├── requirements.txt # Bağımlılıklar
└── run.bat          # Windows için kolay başlatıcı
```

---

## 🖼️ Ekran Görüntüleri
Kapalı Hali: 
<img width="106" height="103" alt="kapalıHal" src="https://github.com/user-attachments/assets/fc6cbff0-c906-4944-ae7d-07ed97d1a446" />

Takvim Açık Hali : 
<img width="641" height="860" alt="Açık Hal" src="https://github.com/user-attachments/assets/330477d1-aae7-4baf-b4c5-7cd62780671b" />


---

## 🛠️ Geliştirme

Katkıda bulunmak istiyorsan:
1. Bu repoyu fork'la
2. Yeni bir branch aç: `git checkout -b ozellik/yeni-ozellik`
3. Değişikliklerini commit'le
4. Pull Request gönder

---

## 📄 Lisans

MIT License — dilediğiniz gibi kullanabilir, değiştirebilirsiniz.

---

## 👨‍💻 Geliştirici

**Aykut TORTOP**

*Python + PyQt6 ile geliştirilmiştir.*
