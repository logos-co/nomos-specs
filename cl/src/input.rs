/// This module defines the partial transaction structure.
///
/// Partial transactions, as the name suggests, are transactions
/// which on their own may not balance (i.e. \sum inputs != \sum outputs)
use crate::{
    error::Error,
    note::{Note, NoteCommitment},
    nullifier::{Nullifier, NullifierNonce, NullifierSecret},
};
use jubjub::{ExtendedPoint, Scalar};

#[derive(Debug, PartialEq, Eq)]
pub struct Input {
    pub note_comm: NoteCommitment,
    pub nullifier: Nullifier,
    pub balance: ExtendedPoint,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InputWitness {
    note: Note,
    nf_sk: NullifierSecret,
    nonce: NullifierNonce,
    balance_blinding: Scalar,
}

// as we don't have SNARKS hooked up yet, the witness will be our proof
pub struct InputProof(InputWitness);

impl Input {
    pub fn from_witness(w: InputWitness) -> Self {
        Self {
            note_comm: w.note.commit(w.nf_sk.commit(), w.nonce),
            nullifier: Nullifier::new(w.nf_sk, w.nonce),
            balance: w.note.balance(w.balance_blinding),
        }
    }

    pub fn prove(&self, w: &InputWitness) -> Result<InputProof, Error> {
        if &Input::from_witness(w.clone()) != self {
            Err(Error::ProofFailed)
        } else {
            Ok(InputProof(w.clone()))
        }
    }

    pub fn verify(&self, proof: &InputProof) -> bool {
        // verification checks the relation
        // - nf_pk == hash(nf_sk)
        // - note_comm == commit(note || nf_pk)
        // - nullifier == hash(nf_sk || nonce)
        // - balance == v * hash_to_curve(Unit) + blinding * H

        let witness = &proof.0;

        let nf_pk = witness.nf_sk.commit();
        self.note_comm == witness.note.commit(nf_pk, witness.nonce)
            && self.nullifier == Nullifier::new(witness.nf_sk, witness.nonce)
            && self.balance == witness.note.balance(witness.balance_blinding)
    }
}

#[cfg(test)]
mod test {
    use group::ff::Field;

    use super::*;
    use crate::{nullifier::NullifierNonce, test_util::seed_rng};

    #[test]
    fn test_input_proof() {
        let mut rng = seed_rng(0);

        let note = Note::new(10, "NMO");
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);
        let balance_blinding = Scalar::random(&mut rng);

        let witness = InputWitness {
            note,
            nf_sk,
            nonce,
            balance_blinding,
        };

        let input = Input::from_witness(witness.clone());
        let proof = input.prove(&witness).unwrap();

        assert!(input.verify(&proof));

        let wrong_witnesses = [
            InputWitness {
                note: Note::new(11, "NMO"),
                ..witness.clone()
            },
            InputWitness {
                note: Note::new(10, "ETH"),
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
            InputWitness {
                balance_blinding: Scalar::random(&mut rng),
                ..witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(input.prove(&wrong_witness).is_err());

            let wrong_note = Input::from_witness(wrong_witness.clone());
            let wrong_proof = wrong_note.prove(&wrong_witness).unwrap();

            assert!(!input.verify(&wrong_proof));
        }
    }
}
