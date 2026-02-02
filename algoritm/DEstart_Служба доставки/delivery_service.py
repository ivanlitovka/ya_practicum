def calculate_platforms(robot_weights: list[int], limit: int) -> int:
    robot_weights.sort()

    left = 0
    right = len(robot_weights) - 1
    platforms = 0

    while left <= right:
        # Если можно поместить двух роботов на платформу
        if robot_weights[left] + robot_weights[right] <= limit:
            left += 1
            right -= 1
        else:
            # Иначе помещаем только тяжелого робота
            right -= 1

        platforms += 1

    return platforms


def main():
    weights_input = input().strip()
    limit_input = input().strip()

    robot_weights = list(map(int, weights_input.split()))
    limit = int(limit_input)

    print(calculate_platforms(robot_weights, limit))


if __name__ == "__main__":
    main()
