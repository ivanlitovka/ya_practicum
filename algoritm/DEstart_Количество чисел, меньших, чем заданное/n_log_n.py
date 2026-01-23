from array import array


def main():
    # Открываем файл для чтения
    with open('input.txt', 'r') as f:
        # Читаем первую строку файла, разбиваем её на части и преобразуем в массив чисел типа 'b'
        numbers = array('b', map(int, f.readline().split()))

    # Создаем отсортированный список кортежей (индекс, значение)
    # enumerate() добавляет индекс к каждому элементу
    # sorted() сортирует по второму элементу кортежа (самому числу)
    sorted_numbers = sorted(enumerate(numbers), key=lambda x: x[1])
    print(sorted_numbers)
    # Создаем результирующий массив той же длины, что и исходный
    # Заполняем его нулями типа 'b'
    result = array('b', [0] * len(numbers))

    # Проходим по отсортированному списку, начиная со второго элемента
    for i in range(1, len(sorted_numbers)):
        # Получаем текущий элемент и предыдущий
        current = sorted_numbers[i]
        previous = sorted_numbers[i-1]

        # Если текущий элемент больше предыдущего
        if current[1] > previous[1]:
            # Записываем в результат позицию текущего элемента
            result[current[0]] = i
        else:
            # Если элементы равны, берем значение из предыдущего
            result[current[0]] = result[previous[0]]

    # Выводим результат через пробел
    print(*result)


if __name__ == '__main__':
    main()
