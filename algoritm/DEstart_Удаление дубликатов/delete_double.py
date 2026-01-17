def main():
    with open('input.txt', 'r') as f:
        len_array = int(f.readline())
        array = list(map(int, f.readline().split()))

    digit = []
    line = []

    for item in range(len_array):
        for doub in range(item+1, len_array):
            if array[item] == array[doub]:
                array[doub] = '_'
        if array[item] == '_':
            line.append(array[item])
        else:
            digit.append(array[item])
    array = list(map(str, sorted(digit))) + line

    with open('output.txt', 'w') as f:
        f.write(' '.join(array))


if __name__ == '__main__':
    main()
