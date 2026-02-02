def sort_containers(arr, template):
    # Создаем словарь для подсчета количества каждого элемента
    count_dict = {}
    for num in arr:
        if num in count_dict:
            count_dict[num] += 1
        else:
            count_dict[num] = 1

    # Создаем результат согласно шаблону
    result = []
    for num in template:
        if num in count_dict:
            # Добавляем все вхождения числа согласно шаблону
            result.extend([num] * count_dict[num])
            # Удаляем обработанный элемент из словаря
            del count_dict[num]

    # Собираем оставшиеся числа, которых не было в шаблоне
    remaining = []
    for num in count_dict:
        remaining.extend([num] * count_dict[num])

    # Сортируем оставшиеся числа и добавляем в конец
    remaining.sort()
    result.extend(remaining)

    return result


# Считываем входные данные
n = int(input())
arr = list(map(int, input().split()))
m = int(input())
template = list(map(int, input().split()))

# Получаем отсортированный результат
sorted_result = sort_containers(arr, template)

# Выводим результат
print(' '.join(map(str, sorted_result)))
