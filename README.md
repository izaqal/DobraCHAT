# DobraCHAT
I2P / Tor proxy destekli matrix clientı ve hesap açma aracı.

Fdroid indirin ve yükleyin: https://f-droid.org/F-Droid.apk

-TOR SUNUCULARI İÇİN- Orbot indirin ve yükleyin: https://guardianproject.info/releases/orbot-latest.apk

-I2P SUNUCULARI İÇİN- Fdroid içinden I2Pd uygulamasını aratın ve onu indirin.

Fdroid içinden termux uygulamasını aratın ve onu indirin.

-TOR SUNUCULARI İÇİN- Orbot uygulamasını açın ve bağlantıyı aktif edin.

-I2P SUNUCULARI İÇİN- I2Pd uygulamasını açın. Bağlantı 1-2 dakika sürebilir.

Termuxa girin ve sırayla bu işlemleri yapın:

	Komutları girin:

	pkg update && pkg upgrade -y

	pkg install python clang libffi openssl make pkg-config -y

	pip install --upgrade pip

	pip install matrix-nio textual aiohttp aiohttp-socks

	termux-setup-storage

		Bu komutu girdiğinizde sizden dosya izni isteyecektir onu onaylayıp tekrar aynı komutu girin ve Y yazıp devam edin

	cd ~/storage/shared/Download/Telegram

		Eğer kodu telegramdan indirdiyseniz bu dizinde olacak.

	python dobrachat.py

Karşınıza sorular çıkacak. Onları uygun şekilde doldurun. Örnek:

	Proxy seçiniz (TOR için T, I2P için I): i

		Büyük-küçük harf duyarlılığı yoktur.

	Bağlanılacak Adres (örn. xyz.onion veya abc.b32.i2p): x3ysi47zulgj4ukdqkl3vykclf3ynmvdcw3ztw4zmhtwq3at5poa.b32.i2p

	Kullanıcı adınız: test2

	Şifreniz: testtest

	Sunucu adı: Deneme

Burada kendi sunucumdan örnek verdim. Siz hangi sunucuya bağlanacaksanız sahibinden bilgi alabilirsiniz.

=======================================================================================================================================

HESAP AÇMA:

	BAŞLANGIÇ İÇİN NOT: Matrix sunucu ayarlarında hesap açma kapalıysa aşağıdaki yöntem çalışmayacaktır. Sunucu sahibinden sizin için hesap oluşturmasını isteyin.

		Hesap açma komutu (sunucu sahibi tarafından girilmeli):

		cd ~/go/pkg/mod/github.com/matrix-org/dendrite@v0.13.8/cmd/create-account

		sudo go run . -config /etc/dendrite/dendrite.yaml -username test2 -password testtest

	Termux'u açın: python dobrahesap.py

	Oradaki sorulara cevap verin, örnek:

		=== DobraCHAT Matrix Hesap Oluşturma Aracı ===

		Proxy türünü seçiniz (TOR için T, I2P için I): i

		[+] I2P proxy aktif edildi (127.0.0.1:4444).

		Bağlanılacak Adres (örn: xyz.onion veya abc.b32.i2p): x3ysi47zulgj4ukdqkl3vykclf3ynmvdcw3ztw4zmhtwq3at5poa.b32.i2p

		Oluşturulacak Kullanıcı Adı: test10

		Şifre: testtest

		[+] http://x3ysi47zulgj4ukdqkl3vykclf3ynmvdcw3ztw4zmhtwq3at5poa.b32.i2p adresine istek atılıyor...

		[✔] HESAP BAŞARIYLA OLUŞTURULDU!

		 User ID    : @test10:Deneme

		 Access Token: w8Y_pz7W6GPyQYrjEYoJnIvGdbgBrzmckHINx-9Zp6A

	 	 Device ID   : bWiZsuaU
