use rand_core::RngCore;
use serde::{Deserialize, Serialize};

use crate::{
    balance::Balance,
    error::Error,
    note::{NoteCommitment, NoteWitness},
    nullifier::{NullifierCommitment, NullifierNonce},
};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Output {
    pub note_comm: NoteCommitment,
    pub balance: Balance,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OutputWitness {
    pub note: NoteWitness,
    pub nf_pk: NullifierCommitment,
    pub nonce: NullifierNonce,
}

impl OutputWitness {
    pub fn random(note: NoteWitness, owner: NullifierCommitment, mut rng: impl RngCore) -> Self {
        Self {
            note,
            nf_pk: owner,
            nonce: NullifierNonce::random(&mut rng),
        }
    }

    pub fn commit_note(&self) -> NoteCommitment {
        self.note.commit(self.nf_pk, self.nonce)
    }

    pub fn commit(&self) -> Output {
        Output {
            note_comm: self.commit_note(),
            balance: self.note.balance(),
        }
    }
}

// as we don't have SNARKS hooked up yet, the witness will be our proof
#[derive(Debug, Clone)]
pub struct OutputProof(OutputWitness);

impl Output {
    pub fn prove(&self, w: &OutputWitness) -> Result<OutputProof, Error> {
        if &w.commit() == self {
            Ok(OutputProof(w.clone()))
        } else {
            Err(Error::ProofFailed)
        }
    }

    pub fn verify(&self, proof: &OutputProof) -> bool {
        // verification checks the relation
        // - note_comm == commit(note || nf_pk)
        // - balance == v * hash_to_curve(Unit) + blinding * H
        let witness = &proof.0;

        self.note_comm == witness.note.commit(witness.nf_pk, witness.nonce)
            && self.balance == witness.note.balance()
    }

    pub fn to_bytes(&self) -> [u8; 64] {
        let mut bytes = [0u8; 64];
        bytes[..32].copy_from_slice(self.note_comm.as_bytes());
        bytes[32..64].copy_from_slice(&self.balance.to_bytes());
        bytes
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::nullifier::NullifierSecret;

    #[test]
    fn test_output_proof() {
        let mut rng = rand::thread_rng();

        let note = NoteWitness::new(10, "NMO", [0u8; 32], &mut rng);
        let nf_pk = NullifierSecret::random(&mut rng).commit();
        let nonce = NullifierNonce::random(&mut rng);

        let witness = OutputWitness { note, nf_pk, nonce };

        let output = witness.commit();
        let proof = output.prove(&witness).unwrap();

        assert!(output.verify(&proof));

        let wrong_witnesses = [
            OutputWitness {
                note: NoteWitness::new(11, "NMO", [0u8; 32], &mut rng),
                ..witness.clone()
            },
            OutputWitness {
                note: NoteWitness::new(10, "ETH", [0u8; 32], &mut rng),
                ..witness.clone()
            },
            OutputWitness {
                nf_pk: NullifierSecret::random(&mut rng).commit(),
                ..witness.clone()
            },
            OutputWitness {
                nonce: NullifierNonce::random(&mut rng),
                ..witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(output.prove(&wrong_witness).is_err());

            let wrong_output = wrong_witness.commit();
            let wrong_proof = wrong_output.prove(&wrong_witness).unwrap();
            assert!(!output.verify(&wrong_proof));
        }
    }
}
