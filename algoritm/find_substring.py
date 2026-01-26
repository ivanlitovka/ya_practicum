# Импортируем число, заведомо большее, чем любая сумма элементов среза.
from sys import maxsize


def find_min_slice_sum(data, elements_in_slice):
    # В переменную min_sum будем сохранять наименьшую сумму,
    # полученную при сравнении двух срезов.
    # В начале работы программы сумма первого среза
    # должна быть признана минимальной и записана в min_sum
    # (ведь других сумм пока что нет).
    # Установим очень большое стартовое значение min_sum.
    min_sum = maxsize
    # Двигаемся от начала массива до последнего элемента,
    # от которого мы сможем взять срез нужной длины.
    for index in range(len(data) - elements_in_slice + 1):
        # В temp_sum будем записывать сумму элементов очередного среза
        # и сравнивать её с min_sum.
        temp_sum = 0
        # Перебираем элементы в срезе.
        for slice_index in range(elements_in_slice):
            # Подсчитываем сумму значений в очередном срезе.
            temp_sum += data[index + slice_index]
        # Выбираем минимальное значение из двух и сохраняем это значение
        # в переменную min_sum.
        print(temp_sum)
        min_sum = temp_sum if temp_sum < min_sum else min_sum
    return min_sum


if __name__ == '__main__':
    data = [5, -3, -2, 10, 2, 7, 1, -6, 13]
    elements_in_slice = 4
    print(find_min_slice_sum(data, elements_in_slice))
