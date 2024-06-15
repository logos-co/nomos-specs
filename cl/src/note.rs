use blake2::{Blake2s256, Digest};
use group::GroupEncoding;
use rand_core::RngCore;

use crate::{
    balance::{Balance, BalanceWitness},
    nullifier::{NullifierCommitment, NullifierNonce},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct NoteCommitment([u8; 32]);

impl NoteCommitment {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

// TODO: Rename Note to NoteWitness and NoteCommitment to Note

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Note {
    pub balance: BalanceWitness,
}

impl Note {
    pub fn random(value: u64, unit: impl Into<String>, rng: impl RngCore) -> Self {
        Self {
            balance: BalanceWitness::random(value, unit, rng),
        }
    }

    pub fn commit(&self, nf_pk: NullifierCommitment, nonce: NullifierNonce) -> NoteCommitment {
        let mut hasher = Blake2s256::new();
        hasher.update(b"NOMOS_CL_NOTE_COMMIT");
        hasher.update(self.balance.value.to_le_bytes());
        hasher.update(self.balance.unit_point().to_bytes());
        // Important! we don't commit to the balance blinding factor as that may make the notes linkable.
        hasher.update(nf_pk.as_bytes());
        hasher.update(nonce.as_bytes());

        let commit_bytes: [u8; 32] = hasher.finalize().into();
        NoteCommitment(commit_bytes)
    }

    pub fn balance(&self) -> Balance {
        Balance::from_witness(self.balance.clone())
    }
}

#[cfg(test)]
mod test {
    use crate::{nullifier::NullifierSecret, test_util::seed_rng};

    use super::*;

    #[test]
    fn test_note_commitments_dont_commit_to_balance_blinding() {
        let mut rng = seed_rng(0);
        let n1 = Note::random(12, "NMO", &mut rng);
        let n2 = Note::random(12, "NMO", &mut rng);

        let nf_pk = NullifierSecret::random(&mut rng).commit();
        let nonce = NullifierNonce::random(&mut rng);

        // Balance blinding factors are different.
        assert_ne!(n1.balance.blinding, n2.balance.blinding);

        // But their commitments are the same.
        assert_eq!(n1.commit(nf_pk, nonce), n2.commit(nf_pk, nonce));
    }
}
