# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.pitch_accents.user_accents import UserAccentData


def main():
    data = UserAccentData()
    formatted = data.create_formatted()
    for key, value in formatted.items():
        print(f"{key=}; {value=}")


if __name__ == "__main__":
    main()
