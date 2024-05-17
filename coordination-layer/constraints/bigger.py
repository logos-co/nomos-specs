from noir_constraint import NoirConstraint, NoirProof


class Bigger:
    def __init__(self, y: int):
        self.y = y
        self.noir = NoirConstraint("bigger")

    def prove(self, x: int) -> NoirProof:
        return self.noir.prove({"x": str(x), "y": str(self.y)})

    def verify(self, proof):
        return self.noir.verify({"y": str(self.y)}, proof)
