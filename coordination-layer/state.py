"""
This module maintains the state of the CL.

Namely we are interested in:
- the set of note commitments
- the set of note nullifiers (spent notes)
- the set of constraints
"""

from dataclasses import dataclass

import note
import constraint


@dataclass
class State:
    commitments: set[note.Commitment]
    nullifiers: set[note.Nullifier]
    constraints: dict[bytes, constraint.Constraint]

    def add_constraint(self, c: constraint.Constraint):
        self.constraints[c.hash()] = c
