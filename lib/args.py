import argparse


class Args:
    def __init__(self, description: str, args: list[tuple[str, type, str]]):
        self.parser = argparse.ArgumentParser(description=description)
        for arg in args:
            self.parser.add_argument(arg[0], type=arg[1], help=arg[2])

    def parse(self) -> argparse.Namespace:
        return self.parser.parse_args()
        