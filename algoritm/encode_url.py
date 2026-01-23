import hashlib
from urllib.parse import urlparse


class MarsURLEncoder:

    def __init__(self):
        self.url_db = {}

    def encode(self, long_url):
        """Кодирует длинную ссылку в короткую вида https://ma.rs/X7NYIol."""
        path = urlparse(long_url).path
        hash_obj = hashlib.shake_128(path.encode('utf-8')).hexdigest(4)
        self.url_db[hash_obj] = long_url
        return f'https://ma.rs/{hash_obj}'

    def decode(self, short_url):
        """Декодирует короткую ссылку вида https://ma.rs/X7NYIol в исходную."""
        path = urlparse(short_url).path.lstrip('/')
        long_url = self.url_db[path]
        return long_url


if __name__ == '__main__':
    url_database = MarsURLEncoder()
    print(url_database.encode('https://mars.attack/base/destroy'))
    print(url_database.encode('https://mars.attack/humman_must_be_catch'))
    print(url_database.decode('https://ma.rs/47c4bc0b'))
    print(url_database.decode('https://ma.rs/0c1847b8'))
    print(url_database.url_db)