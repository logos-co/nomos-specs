use jubjub::{ExtendedPoint, Scalar};

use crate::{
    error::Error,
    note::{Note, NoteCommitment},
    nullifier::{NullifierCommitment, NullifierNonce},
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Output {
    pub note_comm: NoteCommitment,
    pub balance: ExtendedPoint,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutputWitness {
    note: Note,
    nf_pk: NullifierCommitment,
    nonce: NullifierNonce,
    balance_blinding: Scalar,
}

// as we don't have SNARKS hooked up yet, the witness will be our proof
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutputProof(OutputWitness);

impl Output {
    pub fn from_witness(w: OutputWitness) -> Self {
        Self {
            note_comm: w.note.commit(w.nf_pk, w.nonce),
            balance: w.note.balance(w.balance_blinding),
        }
    }

    pub fn prove(&self, w: &OutputWitness) -> Result<OutputProof, Error> {
        if &Self::from_witness(w.clone()) == self {
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
            && self.balance == witness.note.balance(witness.balance_blinding)
    }
}

#[cfg(test)]
mod test {
    use group::ff::Field;

    use super::*;
    use crate::{nullifier::NullifierSecret, test_util::seed_rng};

    #[test]
    fn test_output_proof() {
        let mut rng = seed_rng(0);

        let note = Note::new(10, "NMO");
        let nf_pk = NullifierSecret::random(&mut rng).commit();
        let nonce = NullifierNonce::random(&mut rng);
        let balance_blinding = Scalar::random(&mut rng);

        let witness = OutputWitness {
            note,
            nf_pk,
            nonce,
            balance_blinding,
        };

        let output = Output::from_witness(witness.clone());
        let proof = output.prove(&witness).unwrap();

        assert!(output.verify(&proof));

        let wrong_witnesses = [
            OutputWitness {
                note: Note::new(11, "NMO"),
                ..witness.clone()
            },
            OutputWitness {
                note: Note::new(10, "ETH"),
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
            OutputWitness {
                balance_blinding: Scalar::random(&mut rng),
                ..witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(output.prove(&wrong_witness).is_err());

            let wrong_output = Output::from_witness(wrong_witness.clone());
            let wrong_proof = wrong_output.prove(&wrong_witness).unwrap();
            assert!(!output.verify(&wrong_proof));
        }
    }
}
