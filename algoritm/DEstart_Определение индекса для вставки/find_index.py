def main():
    with open('input.txt', 'r') as f:
        array = list(map(int, f.readline().split()))
        digit = int(f.readline())
    left = 0
    right = len(array) - 1
    flag = False
    while left <= right:
        # Находим в наборе элементов индекс среднего элемента.
        mid = (left + right) // 2
        # Если элемент с этим индексом равен искомому, возвращаем его индекс.
        if array[mid] == digit:
            with open('output.txt', 'w') as f:
                f.write(str(mid))
            flag = True
        # Если средний элемент меньше искомого...
        if array[mid] < digit:
            # ...то изменяем левую границу поиска:
            left = mid + 1
        # Если средний элемент больше искомого...
        else:
            # ...то изменяем правую границу поиска:
            right = mid - 1
    # Если левая граница оказалась больше правой,
    # значит, элемент не найден. Возвращаем None.
    if not flag:
        with open('output.txt', 'w') as f:
            f.write(str(left))


if __name__ == '__main__':
    main()
