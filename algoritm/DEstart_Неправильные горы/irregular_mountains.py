from array import array


def main():
    with open('input.txt', 'r') as f:
        mount = array('b', (map(int, f.readline().split())))
    peak = max(mount)
    if peak == mount[-1] or peak == mount[0] or len(mount) < 3:
        return False

    for up in range(0, mount.index(peak)):
        if mount[up] >= mount[up + 1]:
            return False

    for down in range(mount.index(peak), len(mount) - 1):
        if mount[down] <= mount[down + 1]:
            return False

    return True


if __name__ == '__main__':
    print(main())
