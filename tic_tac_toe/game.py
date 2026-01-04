# game.py
from gameparts import Board


def main():
    game = Board()
    game.display()
    # Тут пользователь вводит координаты ячейки.
    row = int(input('Введите номер строки: '))
    column = int(input('Введите номер столбца: '))
    # В метод make_move передаются те координаты, которые ввёл пользователь.
    game.make_move(row, column, 'X')
    print('Ход сделан!')
    game.display()


if __name__ == '__main__':
    main()
