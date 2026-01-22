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
        long_url = self.url_db.pop(path)
        return long_url


if __name__ == '__main__':
    url_database = MarsURLEncoder()
    url_database.encode('https://mars.attack/base/destroy')
    url_database.encode('https://mars.attack/humman_must_be_catch')
    url_database.decode('https://ma.rs/47c4bc0b')
    url_database.decode('https://ma.rs/0c1847b8')
