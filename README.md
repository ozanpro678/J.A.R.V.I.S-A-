# J.A.R.V.I.S Aİ TÜRKÇE
JARVİS Aİ orjinali Alp Ünlü tarafından geliştrilen (yapay zeka ile) WARBESH tarafından güncellenilmiştir.

Projenin bilgisayarınızda sorunsuz çalışması için aşağıdaki adımları sırasıyla takip etmeniz yeterlidir.

1. Python Sürümü Kurulumu (Önemli!)
Projede kullanılan ses ve otomasyon kütüphanelerinin hatasız çalışması için Python 3.12 sürümü zorunludur. (Daha yeni veya test aşamasındaki sürümler hata verebilir).

Eğer bilgisayarınızda Python yüklü değilse veya farklı bir sürüm varsa kaldırın.

Komut Satırını (CMD) açın ve şu komutla Python 3.12'yi otomatik olarak güvenle kurun:

py install 3.12

Projeyi Bilgisayarınıza İndirin
Projeyi bilgisayarınıza klonlayın veya ZIP olarak indirip bir klasöre çıkarın:


(Not: Eğer iç içe iki klasör varsa, main.py dosyasının olduğu asıl klasörün içinde terminali açtığınızdan emin olun).

Gerekli Kütüphanelerin (Bağımlılıkların) Yüklenmesi
Windows sistemlerde pyaudio ve diğer kritik araçların hata vermeden kurulabilmesi için Python 3.12 ortamını zorlayarak yükleme yapıyoruz. Terminale şu komutu yapıştırın ve işlemlerin bitmesini bekleyin:

py -3.12 -m pip install -r requirements.txt
🚀 Sistemi Başlatma (Ateşleme)

Her şey başarıyla kurulduktan sonra Jarvis'i arayüzüyle birlikte çalıştırmak için terminale şu komutu yazmanız yeterlidir:

py -3.12 main.py
📌 Önemli Ayarlar ve Hatırlatmalar

Jarvis'in tüm fonksiyonlarını tam performansla kullanabilmek için çalıştırmadan önce şunlara dikkat edin:

Takvim ve Hatırlatıcılar: Jarvis'in takviminize erişebilmesi için Windows bilgisayarınızda varsayılan Outlook uygulamasının en az bir kez açılmış ve kurulmuş olması gerekir.

Hava Durumu: Canlı hava durumu verileri için actions/weather.py dosyası içerisine kendi ücretsiz OpenWeatherMap API anahtarınızı eklemeyi unutmayın.

Uygulama Yolları: WhatsApp ve Spotify'ı sesli komutla açabilmek için, bu uygulamaların bilgisayarınızdaki kurulu olduğu yolları actions/open_app.py ve actions/whatsapp.py dosyalarından kontrol edebilirsiniz.

💬 Kullanım ve Komutlar

Jarvis açıldığında fütüristik ekran arayüzüyle sizi karşılayacaktır. Mikrofonunuz üzerinden sesli olarak veya ekrandaki metin kutusunu kullanarak şu komutları test edebilirsiniz:

🗣️ "Jarvis, sistem bilgisini ver."

🗣️ "Jarvis, bugün hava nasıl?"

🗣️ "Jarvis, WhatsApp'ı aç."

🗣️ "Jarvis, ekranımda ne var?" (Screen Vision aktifleşir)

🗣️"Jarvis,  ödev menüsünü aç" (Ödev menüsünü açıp pdf lerinizi yükleyin ve yapay zeka yazpsın)

Ve dahası..

