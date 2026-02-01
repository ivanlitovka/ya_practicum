# рекурсивный метод
def find_winner_iterative(N, K):
    players = list(range(1, N + 1))
    current = 0
    while len(players) > 1:
        eliminate = (current + K - 1) % len(players)
        players.pop(eliminate)
        current = eliminate % len(players)  # следующий старт
    return players[0]


if __name__ == '__main__':
    N = int(input())
    K = int(input())
    print(find_winner_iterative(N, K))


"""
# Итеративный подход

def find_winner_iterative(N, K):
    players = list(range(1, N + 1))
    current = 0
    while len(players) > 1:
        eliminate = (current + K - 1) % len(players)
        players.pop(eliminate)
        current = eliminate % len(players)  # следующий старт
    return players[0]
"""
