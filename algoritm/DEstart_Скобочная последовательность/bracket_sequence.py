def is_correct_bracket_seq():
    with open('input.txt', 'r') as f:
        bracket_seq = f.readline()

    bracket_map = {')': '(', ']': '[', '}': '{'}
    stack = []

    for item in bracket_seq:
        if item in '([{':
            stack.append(item)
        elif item in ')]}':
            if not stack or stack[-1] != bracket_map[item]:
                return False
            stack.pop()
    if stack:
        return False
    return True


if __name__ == '__main__':
    print(is_correct_bracket_seq())
