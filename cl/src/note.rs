use jubjub::{ExtendedPoint, Scalar};
use lazy_static::lazy_static;

use crate::crypto;

lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: ExtendedPoint =
        crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

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

    pub fn balance(&self, blinding: Scalar) -> ExtendedPoint {
        let value_scalar = Scalar::from(self.value);
        let unit_point = crypto::hash_to_curve(self.unit.as_bytes());

        unit_point * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
    }
}

#[test]
fn test_note_balance() {
    // balances are blinded
    let a = Note::new(10, "NMO");
    assert_ne!(a.balance(12.into()), a.balance(8.into()));

    // balances are deterministic
    assert_eq!(a.balance(12.into()), a.balance(12.into()));

    // balances are be homomorphic
    let r = Scalar::from(32);
    let ten = Note::new(10, "NMO");
    let eight = Note::new(8, "NMO");
    let two = Note::new(2, "NMO");
    assert_eq!(ten.balance(r) - eight.balance(r), two.balance(r - r));

    assert_eq!(
        ten.balance(54.into()) - ten.balance(48.into()),
        Note::new(0, "NMO").balance(6.into())
    );

    // Unit's differentiate between values.
    let d = Note::new(10, "ETH");
    assert_ne!(a.balance(r), d.balance(r));

    // Zero is the same across all units
    assert_eq!(
        Note::new(0, "NMO").balance(r),
        Note::new(0, "ETH").balance(r)
    );
}
