"""
This module provides the interface for loading, proving and verifying constraints written in noir.

The assumptions of this module:
- noir constraints are defined as a noir package in `./noir/crates/<constraint>/`
- ./noir is relative to this file

For ergonomics, one should provide python wrappers that understands the API of
the corresponding constraint.
"""

from dataclasses import dataclass
from pathlib import Path

import sh
import portalocker
import tempfile
import toml


from constraints import Proof

NOIR_DIR = Path(__file__).resolve().parent.parent / "noir"
LOCK_FILE = NOIR_DIR / ".CL.lock"
CONSTRAINTS_DIR = NOIR_DIR / "crates"

NARGO = sh.Command("nargo")


@dataclass
class NoirProof(Proof):
    proof: str


class NoirConstraint:
    """
    Provides a wrapper around the `nargo` command for interacting with a constraint
    written in Noir.

    E.g. NoirConstraint("bigger") corresponds to the noir circuit defined
    in "./noir/crates/bigger/".

    Calling API methods on this object will map to shelling out to `nargo` to execute
    the relevant `nargo` action.

    Efforts are taken to make this wrapper thread safe.To prevent any race
    conditions we limit one action at any one time across the `./noir` directory.
    """

    def __init__(self, name: str):
        self.name = name
        assert self.noir_package_dir.exists() and self.noir_package_dir.is_dir()
        self._prepare()

    @property
    def noir_package_dir(self):
        return CONSTRAINTS_DIR / self.name

    def prove(self, params: dict) -> NoirProof:
        """
        Attempts to prove the noir constraint with the given paramaters.
        1. Write the paramaters to the noir Prover.toml file
        2. execute `nargo prove`
        3. Retreive the proof written by nargo.

        Returns the NoirProof containing the proof of the statment.
        """
        with portalocker.TemporaryFileLock(LOCK_FILE):
            with open(self.noir_package_dir / "Prover.toml", "w") as prover_f:
                toml.dump(params, prover_f)

            prove_res = self._nargo("prove", _return_cmd=True)
            assert prove_res.exit_code == 0

            with open(NOIR_DIR / "proofs" / f"{self.name}.proof", "r") as proof:
                return NoirProof(proof.read())

    def verify(self, params: dict, proof: NoirProof):
        """
        Attempts to verify a proof given the public paramaters.
        1. Write the public paramaters to the Verifier.toml
        2. Write the proof to the location nargo expects it
        3. Execute `nargo verify`
        4. Check the process exit code.
        """
        with portalocker.TemporaryFileLock(LOCK_FILE):
            with open(self.noir_package_dir / "Verifier.toml", "w") as verifier_f:
                toml.dump(params, verifier_f)

            with open(NOIR_DIR / "proofs" / f"{self.name}.proof", "w") as proof_file:
                proof_file.write(proof.proof)
            verify_res = self._nargo("verify", _ok_code=[0, 1], _return_cmd=True)
            return verify_res.exit_code == 0

    def _nargo(self, *args, **kwargs):
        return NARGO(*args, **kwargs, _cwd=self.noir_package_dir)

    def _prepare(self):
        """
        Verify that the Noir circuit is well defined.
        """
        check = self._nargo("check", _return_cmd=True)
        assert check.exit_code == 0
        compile = self._nargo("compile", _return_cmd=True)
        assert compile.exit_code == 0
