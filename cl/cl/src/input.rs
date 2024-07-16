/// This module defines the partial transaction structure.
///
/// Partial transactions, as the name suggests, are transactions
/// which on their own may not balance (i.e. \sum inputs != \sum outputs)
use crate::{
    balance::Balance,
    note::{DeathCommitment, NoteWitness},
    nullifier::{Nullifier, NullifierNonce, NullifierSecret},
};
use rand_core::RngCore;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Input {
    pub nullifier: Nullifier,
    pub balance: Balance,
    pub death_cm: DeathCommitment,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
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
            nullifier: Nullifier::new(self.nf_sk, self.nonce),
            balance: self.note.balance(),
            death_cm: self.note.death_commitment(),
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
    pub fn to_bytes(&self) -> [u8; 64] {
        let mut bytes = [0u8; 64];
        bytes[..32].copy_from_slice(self.nullifier.as_bytes());
        bytes[32..64].copy_from_slice(&self.balance.to_bytes());
        bytes[64..96].copy_from_slice(&self.death_cm.0);
        bytes
    }
}
