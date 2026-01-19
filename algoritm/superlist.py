def list_superset(list_set_1, list_set_2):
    # Не меняйте названия функции и параметров. Напишите решение здесь.
    long, short = (
        (list_set_1, list_set_2)
        if len(list_set_1) >= len(list_set_2)
        else (list_set_2, list_set_1)
    )
    for item in short:
        if item in long:
            flag = True
            continue
        else:
            result = 'Супермножество не обнаружено.'
            flag = False
            break
    if flag and len(long) == len(short):
        result = 'Наборы равны.'
    if flag and len(long) > len(short):
        result = f'Набор {long} - супермножество.'
    return result


# Примеры для проверки функции.
list_set_1 = [1, 3, 5, 7]
list_set_2 = [3, 5]
list_set_3 = [5, 3, 7, 1]
list_set_4 = [5, 6]

print(list_superset(list_set_1, list_set_2))
print(list_superset(list_set_2, list_set_3))
print(list_superset(list_set_1, list_set_3))
print(list_superset(list_set_2, list_set_4))
