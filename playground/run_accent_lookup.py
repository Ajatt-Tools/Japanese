# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.mecab_controller import to_katakana


def main() -> None:
    acc_dict = read_formatted_accents()
    for item in acc_dict[to_katakana("経緯")]:
        print(item)
    for item in acc_dict[to_katakana("国境")]:
        print(item)


if __name__ == "__main__":
    main()
