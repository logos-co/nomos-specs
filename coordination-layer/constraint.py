from dataclasses import dataclass


@dataclass
class Constraint:

    def hash(self) -> bytes:
        raise NotImplementedError()
