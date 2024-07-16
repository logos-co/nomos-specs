use rand_core::CryptoRngCore;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::{
    balance::{Balance, BalanceWitness},
    nullifier::{NullifierCommitment, NullifierNonce},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct DeathCommitment(pub [u8; 32]);

pub fn death_commitment(death_constraint: &[u8]) -> DeathCommitment {
    let mut hasher = Sha256::new();
    hasher.update(b"NOMOS_CL_DEATH_COMMIT");
    hasher.update(death_constraint);
    let death_cm: [u8; 32] = hasher.finalize().into();

    DeathCommitment(death_cm)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct NoteCommitment([u8; 32]);

impl NoteCommitment {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

// TODO: Rename Note to NoteWitness and NoteCommitment to Note

#[derive(Debug, PartialEq, Eq, Clone, Copy, Serialize, Deserialize)]
pub struct NoteWitness {
    pub balance: BalanceWitness,
    pub death_constraint: [u8; 32], // death constraint verification key
    pub state: [u8; 32],
}

impl NoteWitness {
    pub fn new(
        value: u64,
        unit: impl Into<String>,
        state: [u8; 32],
        rng: impl CryptoRngCore,
    ) -> Self {
        Self {
            balance: BalanceWitness::random(value, unit, rng),
            death_constraint: [0u8; 32],
            state,
        }
    }

    pub fn commit(&self, nf_pk: NullifierCommitment, nonce: NullifierNonce) -> NoteCommitment {
        let mut hasher = Sha256::new();
        hasher.update(b"NOMOS_CL_NOTE_COMMIT");

        // COMMIT TO BALANCE
        hasher.update(self.balance.value.to_le_bytes());
        hasher.update(self.balance.unit.compress().to_bytes());
        // Important! we don't commit to the balance blinding factor as that may make the notes linkable.

        // COMMIT TO STATE
        hasher.update(self.state);

        // COMMIT TO DEATH CONSTRAINT
        hasher.update(self.death_constraint);

        // COMMIT TO NULLIFIER
        hasher.update(nf_pk.as_bytes());
        hasher.update(nonce.as_bytes());

        let commit_bytes: [u8; 32] = hasher.finalize().into();
        NoteCommitment(commit_bytes)
    }

    pub fn balance(&self) -> Balance {
        self.balance.commit()
    }

    pub fn death_commitment(&self) -> DeathCommitment {
        death_commitment(&self.death_constraint)
    }
}

#[cfg(test)]
mod test {
    use crate::nullifier::NullifierSecret;

    use super::*;

    #[test]
    fn test_note_commitments_dont_commit_to_balance_blinding() {
        let mut rng = rand::thread_rng();
        let n1 = NoteWitness::new(12, "NMO", [0u8; 32], &mut rng);
        let n2 = NoteWitness::new(12, "NMO", [0u8; 32], &mut rng);

        let nf_pk = NullifierSecret::random(&mut rng).commit();
        let nonce = NullifierNonce::random(&mut rng);

        // Balance blinding factors are different.
        assert_ne!(n1.balance.blinding, n2.balance.blinding);

        // But their commitments are the same.
        assert_eq!(n1.commit(nf_pk, nonce), n2.commit(nf_pk, nonce));
    }
}
