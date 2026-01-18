example_array = [6, 5, 3, 1, 8, 7, 2, 4]


def bubble_sort(data):
    last_index = len(data) - 1
    for index in range(len(data)):
        swapped = False
        for item in range(last_index):
            if data[item] > data[item + 1]:
                data[item], data[item + 1] = data[item + 1], data[item]
                swapped = True
#        print(data)
        if swapped:
            last_index -= 1
        else:
            break
    return data


print(bubble_sort(example_array))
