/// This module defines the partial transaction structure.
///
/// Partial transactions, as the name suggests, are transactions
/// which on their own may not balance (i.e. \sum inputs != \sum outputs)
use crate::{
    balance::Balance,
    note::{NoteCommitment, NoteWitness},
    nullifier::{Nullifier, NullifierNonce, NullifierSecret},
};
use rand_core::RngCore;
// use risc0_groth16::{PublicInputsJson, Verifier};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Input {
    pub note_comm: NoteCommitment,
    pub nullifier: Nullifier,
    pub balance: Balance,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InputWitness {
    pub note: NoteWitness,
    pub nf_sk: NullifierSecret,
    pub nonce: NullifierNonce,
}

impl InputWitness {
    pub fn random(note: NoteWitness, mut rng: impl RngCore) -> Self {
        Self {
            note,
            nf_sk: NullifierSecret::random(&mut rng),
            nonce: NullifierNonce::random(&mut rng),
        }
    }

    pub fn commit(&self) -> Input {
        Input {
            note_comm: self.note.commit(self.nf_sk.commit(), self.nonce),
            nullifier: Nullifier::new(self.nf_sk, self.nonce),
            balance: self.note.balance(),
        }
    }

    pub fn to_output_witness(&self) -> crate::OutputWitness {
        crate::OutputWitness {
            note: self.note.clone(),
            nf_pk: self.nf_sk.commit(),
            nonce: self.nonce,
        }
    }
}

impl Input {
    // pub fn prove(
    //     &self,
    //     w: &InputWitness,
    //     ptx_root: PtxRoot,
    //     death_proof: Vec<u8>,
    // ) -> Result<InputProof, Error> {
    //     if bincode::serialize(&w.commit()).unwrap() != bincode::serialize(&self).unwrap() {
    //         Err(Error::ProofFailed)
    //     } else {
    //         Ok(InputProof {
    //             input: w.clone(),
    //             ptx_root,
    //             death_proof,
    //         })
    //     }
    // }

    // pub fn verify(&self, ptx_root: PtxRoot, proof: &InputProof) -> bool {
    //     // verification checks the relation
    //     // - nf_pk == hash(nf_sk)
    //     // - note_comm == commit(note || nf_pk)
    //     // - nullifier == hash(nf_sk || nonce)
    //     // - balance == v * hash_to_curve(Unit) + blinding * H
    //     // - ptx_root is the same one that was used in proving.

    //     let witness = &proof.input;

    //     let nf_pk = witness.nf_sk.commit();

    //     // let death_constraint_was_committed_to =
    //     //     witness.note.death_constraint == bincode::serialize(&death_constraint).unwrap();

    //     // let death_constraint_is_satisfied: bool = Verifier::from_json(
    //     //     bincode::deserialize(&proof.death_proof).unwrap(),
    //     //     PublicInputsJson {
    //     //         values: vec![ptx_root.hex()],
    //     //     },
    //     //     bincode::deserialize(&witness.note.death_constraint).unwrap(),
    //     // )
    //     // .unwrap()
    //     // .verify()
    //     // .is_ok();
    //     let death_constraint_is_satisfied = true;
    //     self.note_comm == witness.note.commit(nf_pk, witness.nonce)
    //         && self.nullifier == Nullifier::new(witness.nf_sk, witness.nonce)
    //         && self.balance == witness.note.balance()
    //         && ptx_root == proof.ptx_root
    //         // && death_constraint_was_committed_to
    //         && death_constraint_is_satisfied
    // }

    pub fn to_bytes(&self) -> [u8; 96] {
        let mut bytes = [0u8; 96];
        bytes[..32].copy_from_slice(self.note_comm.as_bytes());
        bytes[32..64].copy_from_slice(self.nullifier.as_bytes());
        bytes[64..96].copy_from_slice(&self.balance.to_bytes());
        bytes
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::{nullifier::NullifierNonce, test_util::seed_rng};

    #[test]
    fn test_input_proof() {
        let mut rng = seed_rng(0);

        let ptx_root = PtxRoot::default();

        let note = NoteWitness::new(10, "NMO", [0u8; 32], &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let input_witness = InputWitness { note, nf_sk, nonce };

        let input = input_witness.commit();
        let proof = input.prove(&input_witness, ptx_root, vec![]).unwrap();

        assert!(input.verify(ptx_root, &proof));

        let wrong_witnesses = [
            InputWitness {
                note: NoteWitness::new(11, "NMO", [0u8; 32], &mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                note: NoteWitness::new(10, "ETH", [0u8; 32], &mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                nf_sk: NullifierSecret::random(&mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                nonce: NullifierNonce::random(&mut rng),
                ..input_witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(input.prove(&wrong_witness, ptx_root, vec![]).is_err());

            let wrong_input = wrong_witness.commit();
            let wrong_proof = wrong_input.prove(&wrong_witness, ptx_root, vec![]).unwrap();
            assert!(!input.verify(ptx_root, &wrong_proof));
        }
    }

    #[test]
    fn test_input_ptx_coupling() {
        let mut rng = seed_rng(0);

        let note = NoteWitness::new(10, "NMO", [0u8; 32], &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let witness = InputWitness { note, nf_sk, nonce };

        let input = witness.commit();

        let ptx_root = PtxRoot::random(&mut rng);
        let proof = input.prove(&witness, ptx_root, vec![]).unwrap();

        assert!(input.verify(ptx_root, &proof));

        // The same input proof can not be used in another partial transaction.
        let another_ptx_root = PtxRoot::random(&mut rng);
        assert!(!input.verify(another_ptx_root, &proof));
    }
}
