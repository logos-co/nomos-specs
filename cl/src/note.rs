use blake2::{Blake2s256, Digest};
use group::GroupEncoding;
use jubjub::{ExtendedPoint, Scalar};
use lazy_static::lazy_static;

use crate::{
    crypto,
    nullifier::{NullifierCommitment, NullifierNonce},
};

lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: ExtendedPoint =
        crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

#[derive(Debug, PartialEq, Eq)]
pub struct NoteCommitment([u8; 32]);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Note {
    pub value: u64,
    pub unit: String,
}

impl Note {
    pub fn new(value: u64, unit: impl Into<String>) -> Self {
        Self {
            value,
            unit: unit.into(),
        }
    }

    pub fn unit_point(&self) -> ExtendedPoint {
        crypto::hash_to_curve(self.unit.as_bytes())
    }

    pub fn balance(&self, blinding: Scalar) -> ExtendedPoint {
        let value_scalar = Scalar::from(self.value);
        self.unit_point() * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
    }

    pub fn commit(&self, nf_pk: NullifierCommitment, nonce: NullifierNonce) -> NoteCommitment {
        let mut hasher = Blake2s256::new();
        hasher.update(b"NOMOS_CL_NOTE_COMMIT");
        hasher.update(self.value.to_le_bytes());
        hasher.update(self.unit_point().to_bytes());
        hasher.update(nf_pk.as_bytes());
        hasher.update(nonce.as_bytes());

        let commit_bytes: [u8; 32] = hasher.finalize().into();
        NoteCommitment(commit_bytes)
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_balance_zero_unitless() {
        // Zero is the same across all units
        let r = Scalar::from(32);
        assert_eq!(
            Note::new(0, "NMO").balance(r),
            Note::new(0, "ETH").balance(r)
        );
    }

    #[test]
    fn test_balance_blinding() {
        // balances are blinded
        let r1 = Scalar::from(12);
        let r2 = Scalar::from(8);
        let a = Note::new(10, "NMO");
        assert_ne!(a.balance(r1), a.balance(r2));
        assert_eq!(a.balance(r1), a.balance(r1));
    }

    #[test]
    fn test_balance_units() {
        // Unit's differentiate between values.
        let nmo = Note::new(10, "NMO");
        let eth = Note::new(10, "ETH");
        let r = Scalar::from(1337);
        assert_ne!(nmo.balance(r), eth.balance(r));
    }

    #[test]
    fn test_balance_homomorphism() {
        let r = Scalar::from(32);
        let ten = Note::new(10, "NMO");
        let eight = Note::new(8, "NMO");
        let two = Note::new(2, "NMO");
        assert_eq!(ten.balance(r) - eight.balance(r), two.balance(0.into()));

        assert_eq!(
            ten.balance(54.into()) - ten.balance(48.into()),
            Note::new(0, "NMO").balance(6.into())
        );
    }
}
