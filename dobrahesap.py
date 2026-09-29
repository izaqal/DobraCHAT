import sys
import requests

def main():
    print("=== DobraCHAT Matrix Hesap Oluşturma Aracı ===")

    # 1. Proxy Seçimi
    proxy_secim = input("Proxy türünü seçiniz (TOR için T, I2P için I): ").strip().upper()

    proxies = {}
    if proxy_secim == "T":
        # Tor SOCKS5 Proxy (Varsayılan Port: 9050)
        proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        print("[+] Tor proxy aktif edildi (127.0.0.1:9050).")
    elif proxy_secim == "I":
        # I2P HTTP Proxy (Varsayılan Port: 4444)
        proxies = {
            'http': 'http://127.0.0.1:4444',
            'https': 'http://127.0.0.1:4444'
        }
        print("[+] I2P proxy aktif edildi (127.0.0.1:4444).")
    else:
        print("[-] Hatalı seçim yaptınız. Sadece T veya I giriniz.")
        sys.exit(1)

    # 2. Sunucu Adresi
    sunucu = input("Bağlanılacak Adres (örn: xyz.onion veya abc.b32.i2p): ").strip()
    if not sunucu.startswith("http://") and not sunucu.startswith("https://"):
        homeserver_url = f"http://{sunucu}"
    else:
        homeserver_url = sunucu

    # 3. Hesap Bilgileri
    username = input("Oluşturulacak Kullanıcı Adı: ").strip()
    password = input("Şifre: ").strip()

    # Matrix Register API Endpoint
    register_url = f"{homeserver_url}/_matrix/client/v3/register"

    # Kayıt İsteği Gövdesi (m.login.dummy tipi açık kayıtlar için standarttır)
    payload = {
        "username": username,
        "password": password,
        "auth": {
            "type": "m.login.dummy"
        }
    }

    print(f"\n[+] {homeserver_url} adresine istek atılıyor...")

    try:
        response = requests.post(
            register_url,
            json=payload,
            proxies=proxies,
            timeout=20
        )

        if response.status_code == 200:
            data = response.json()
            print("\n[✔] HESAP BAŞARIYLA OLUŞTURULDU! DobraCHAT hesabınızı kullanmaya başlayabilirsiniz:")
            print(f" User ID    : {data.get('user_id')}")
            print(f" Access Token: {data.get('access_token')}")
            print(f" Device ID   : {data.get('device_id')}")
        else:
            print(f"\n[✖] Kayıt Başarısız (Status Code: {response.status_code})")
            try:
                err_data = response.json()
                print(f" Hata Kodu : {err_data.get('errcode')}")
                print(f" Açıklama  : {err_data.get('error')}")
            except Exception:
                print(f" Sunucu Yanıtı: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\n[!] Bağlantı Sağlanamadı: {e}")

if __name__ == "__main__":
    main()

