def max_blocks(arr):
    n = len(arr)
    blocks = 0
    i = 0

    while i < n:
        # Находим максимальное значение в текущем блоке
        max_val = arr[i]
        j = i + 1

        # Ищем конец блока
        while j < n and j <= max_val:
            if arr[j] > max_val:
                max_val = arr[j]
            j += 1

        # Увеличиваем счетчик блоков
        blocks += 1
        i = j

    return blocks


# Чтение входных данных
n = int(input())
arr = list(map(int, input().split()))

# Вывод результата
print(max_blocks(arr))
