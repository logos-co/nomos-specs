"""
This module defines the Constraint interface.

Constraints are the predicates that must be satisfied in order to destroy or create a note.

The logic of a constraint is implemented in a ZK Circuit, and then wrapped in a python interface
for interacting with the rest of the the system.
"""

from dataclasses import dataclass


class Constraint:
    def hash(self) -> bytes:
        raise NotImplementedError()
