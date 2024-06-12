use blake2::{Blake2s256, Digest};
use group::Group;
use jubjub::{AffinePoint, ExtendedPoint, Scalar};
use lazy_static::lazy_static;
use rand_chacha::ChaCha20Rng;
use rand_core::SeedableRng;

lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: ExtendedPoint =
        hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

fn hash_to_curve(bytes: &[u8]) -> ExtendedPoint {
    let mut hasher = Blake2s256::new();
    hasher.update(b"NOMOS_HASH_TO_CURVE");
    hasher.update(bytes);
    let seed: [u8; 32] = hasher.finalize().into();
    ExtendedPoint::random(ChaCha20Rng::from_seed(seed))
}

struct Note {
    value: u64,
    unit: String,
}

impl Note {
    fn new(value: u64, unit: impl Into<String>) -> Self {
        Self {
            value,
            unit: unit.into(),
        }
    }

    fn balance(&self, blinding: Scalar) -> ExtendedPoint {
        let value_scalar = Scalar::from(self.value);
        let unit_point = hash_to_curve(self.unit.as_bytes());

        unit_point * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
    }
}

fn main() {
    println!("Hello, world!");
}

#[test]
fn test_note_balance() {
    let r = Scalar::from(32);

    let a = Note::new(10, "NMO");
    let b = Note::new(10, "NMO");
    assert_eq!(a.balance(r), b.balance(r));

    // balances are be homomorphic
    assert_eq!(
        AffinePoint::from(Note::new(10, "NMO").balance(r) - Note::new(8, "NMO").balance(r)),
        AffinePoint::from(Note::new(2, "NMO").balance(r - r))
    );

    let d = Note::new(10, "ETH");

    assert_ne!(a.balance(r), d.balance(r))
}
