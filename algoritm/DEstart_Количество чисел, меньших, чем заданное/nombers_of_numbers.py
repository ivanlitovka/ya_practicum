from array import array


def main():
    with open('input.txt', 'r') as f:
        numbers = array('b', (map(int, f.readline().split())))

    result = array('b', )

    for number in numbers:
        count = 0
        for n_number in numbers:
            if n_number < number:
                count += 1
        result.append(count)

    print(*result)


if __name__ == '__main__':
    main()
