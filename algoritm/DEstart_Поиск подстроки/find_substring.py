def find_substr():
    with open('input.txt', 'r') as f:
        substr = f.readline().strip()

    left = 0
    max_len = 0

    for right in range(len(substr)):
        if substr[right] in substr[left:right]:
            # Сдвигаем левую границу на позицию после последнего вхождения символа
            left = substr[left:right].rfind(substr[right]) + left + 1
        current_len = right - left + 1
        max_len = max(max_len, current_len)

    print(max_len)


if __name__ == '__main__':
    find_substr()


# Решение через словарь
'''
def longest_unique_substring(s):
    left = 0
    max_len = 0
    char_index = {}  # словарь: символ → последний индекс

    for right in range(len(s)):
        symbol = s[right]
        
        # Если символ уже встречался и находится в текущем окне
        if symbol in char_index and char_index[symbol] >= left:
            left = char_index[symbol] + 1
        
        # Обновляем последний индекс символа
        char_index[symbol] = right
        
        # Вычисляем длину текущего окна
        current_len = right - left + 1
        if current_len > max_len:
            max_len = current_len

    return max_len

# Чтение ввода и вывод результата
s = input().strip()
print(longest_unique_substring(s))

'''
