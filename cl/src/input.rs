/// This module defines the partial transaction structure.
///
/// Partial transactions, as the name suggests, are transactions
/// which on their own may not balance (i.e. \sum inputs != \sum outputs)
use crate::{
    balance::Balance,
    error::Error,
    note::{Note, NoteCommitment},
    nullifier::{Nullifier, NullifierNonce, NullifierSecret},
    partial_tx::PtxCommitment,
};
use rand_core::RngCore;
use risc0_groth16::{ProofJson, PublicInputsJson, Verifier};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Input {
    pub note_comm: NoteCommitment,
    pub nullifier: Nullifier,
    pub balance: Balance,
}

#[derive(Debug, Clone)]
pub struct InputWitness {
    pub note: Note,
    pub nf_sk: NullifierSecret,
    pub nonce: NullifierNonce,
}

impl InputWitness {
    pub fn random(note: Note, mut rng: impl RngCore) -> Self {
        Self {
            note,
            nf_sk: NullifierSecret::random(&mut rng),
            nonce: NullifierNonce::random(&mut rng),
        }
    }
}

// as we don't have SNARKS hooked up yet, the witness will be our proof
#[derive(Debug)]
pub struct InputProof {
    input: InputWitness,
    ptx_comm: PtxCommitment,
    death_proof: ProofJson,
}

impl InputProof {
    fn clone_death_proof(&self) -> ProofJson {
        let bytes = bincode::serialize(&self.death_proof).unwrap();
        bincode::deserialize(&bytes).unwrap()
    }
}

impl Input {
    pub fn from_witness(w: InputWitness) -> Self {
        Self {
            note_comm: w.note.commit(w.nf_sk.commit(), w.nonce),
            nullifier: Nullifier::new(w.nf_sk, w.nonce),
            balance: w.note.balance(),
        }
    }

    pub fn prove(
        &self,
        w: &InputWitness,
        ptx_comm: PtxCommitment,
        death_proof: ProofJson,
    ) -> Result<InputProof, Error> {
        if bincode::serialize(&Input::from_witness(w.clone())).unwrap()
            != bincode::serialize(&self).unwrap()
        {
            Err(Error::ProofFailed)
        } else {
            Ok(InputProof {
                input: w.clone(),
                ptx_comm,
                death_proof,
            })
        }
    }

    pub fn verify(&self, ptx_comm: PtxCommitment, proof: &InputProof) -> bool {
        // verification checks the relation
        // - nf_pk == hash(nf_sk)
        // - note_comm == commit(note || nf_pk)
        // - nullifier == hash(nf_sk || nonce)
        // - balance == v * hash_to_curve(Unit) + blinding * H
        // - ptx_comm is the same one that was used in proving.

        let witness = &proof.input;

        let nf_pk = witness.nf_sk.commit();

        // let death_constraint_was_committed_to =
        //     witness.note.death_constraint == bincode::serialize(&death_constraint).unwrap();

        let death_constraint_is_satisfied: bool = Verifier::from_json(
            proof.clone_death_proof(),
            PublicInputsJson {
                values: vec![ptx_comm.hex()],
            },
            bincode::deserialize(&witness.note.death_constraint).unwrap(),
        )
        .unwrap()
        .verify()
        .is_ok();
        self.note_comm == witness.note.commit(nf_pk, witness.nonce)
            && self.nullifier == Nullifier::new(witness.nf_sk, witness.nonce)
            && self.balance == witness.note.balance()
            && ptx_comm == proof.ptx_comm
            // && death_constraint_was_committed_to
            && death_constraint_is_satisfied
    }

    pub(crate) fn to_bytes(&self) -> [u8; 96] {
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

        let ptx_comm = PtxCommitment::default();

        let note = Note::random(10, "NMO", &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let witness = InputWitness { note, nf_sk, nonce };

        let input = Input::from_witness(witness.clone());
        let proof = input.prove(&witness, ptx_comm).unwrap();

        assert!(input.verify(ptx_comm, &proof));

        let wrong_witnesses = [
            InputWitness {
                note: Note::random(11, "NMO", &mut rng),
                ..witness.clone()
            },
            InputWitness {
                note: Note::random(10, "ETH", &mut rng),
                ..witness.clone()
            },
            InputWitness {
                nf_sk: NullifierSecret::random(&mut rng),
                ..witness.clone()
            },
            InputWitness {
                nonce: NullifierNonce::random(&mut rng),
                ..witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(input.prove(&wrong_witness, ptx_comm).is_err());

            let wrong_input = Input::from_witness(wrong_witness.clone());
            let wrong_proof = wrong_input.prove(&wrong_witness, ptx_comm).unwrap();
            assert!(!input.verify(ptx_comm, &wrong_proof));
        }
    }

    #[test]
    fn test_input_ptx_coupling() {
        let mut rng = seed_rng(0);

        let note = Note::random(10, "NMO", &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let witness = InputWitness { note, nf_sk, nonce };

        let input = Input::from_witness(witness.clone());

        let ptx_comm = PtxCommitment::random(&mut rng);
        let proof = input.prove(&witness, ptx_comm).unwrap();

        assert!(input.verify(ptx_comm, &proof));

        // The same input proof can not be used in another partial transaction.
        let another_ptx_comm = PtxCommitment::random(&mut rng);
        assert!(!input.verify(another_ptx_comm, &proof));
    }
}
