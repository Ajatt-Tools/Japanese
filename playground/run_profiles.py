# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from playground.utils import NoAnkiConfigView


def main():
    config = NoAnkiConfigView()

    for p in config.iter_profiles():
        print(p)


if __name__ == "__main__":
    main()
