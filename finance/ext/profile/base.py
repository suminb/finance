class BaseProfile:
    def __init__(self):
        raise NotImplementedError

    def parse(self, raw: str):
        raise NotImplementedError
