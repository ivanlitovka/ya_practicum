# game.py

from gameparts import Board
from gameparts.exceptions import FieldIndexError


def main():
    game = Board()
    game.display()

    # Запускается бесконечный цикл.
    while True:
        # В этом блоке содержатся операции, которые могут вызвать исключение.
        try:
            # Пользователь вводит значение номера строки.
            row = int(input('Введите номер строки: '))
            # Если введённое число меньше 0 или больше
            # или равно game.field_size...
            if row < 0 or row >= game.field_size:
                # ...выбрасывается собственное исключение FieldIndexError.
                raise FieldIndexError
            column = int(input('Введите номер столбца: '))
            # Если введённое число меньше 0 или больше
            # или равно game.field_size...
            if column < 0 or column >= game.field_size:
                # ...выбрасывается собственное исключение FieldIndexError.
                raise FieldIndexError
        # Если возникает исключение FieldIndexError...
        except FieldIndexError:
            # ...выводятся сообщения...
            print(
                'Значение должно быть неотрицательным и меньше '
                f'{game.field_size}.'
            )
            print('Пожалуйста, введите значения для строки и столбца заново.')
            # ...и цикл начинает свою работу сначала,
            # предоставляя пользователю ещё одну попытку ввести данные.
            continue
        except ValueError:
            print('Буквы вводить нельзя. Только числа.')
            print('Пожалуйста, введите значения для строки и столбца заново.')
            continue
        # Если в блоке try исключения не возникло...
        else:
            # ...значит, введённые значения прошли все проверки
            # и могут быть использованы в дальнейшем.
            # Цикл прерывается.
            break

    game.make_move(row, column, 'X')
    print('Ход сделан!')
    game.display()


if __name__ == '__main__':
    main()
