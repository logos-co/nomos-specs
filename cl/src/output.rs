use jubjub::{ExtendedPoint, Scalar};

use crate::{
    note::{Note, NoteCommitment},
    nullifier::{NullifierCommitment, NullifierNonce},
};

pub struct Output {
    pub note_comm: NoteCommitment,
    pub balance: ExtendedPoint,
}

pub struct OutputWitness {
    note: Note,
    nf_pk: NullifierCommitment,
    nonce: NullifierNonce,
    balance_blinding: Scalar,
}

// as we don't have SNARKS hooked up yet, the witness will be our proof
pub struct OutputProof(OutputWitness);

impl Output {
    pub fn prove(&self, w: OutputWitness) -> OutputProof {
        OutputProof(w)
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
