def baro_fibo(n):
    if n < 0:
        return None
    if n <= 1:
        return 1
    return baro_fibo(n - 1) + baro_fibo(n - 2)


if __name__ == '__main__':
    n = int(input())
    print(baro_fibo(n))
