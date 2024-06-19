use group::{ff::Field, GroupEncoding};
use jubjub::{Scalar, SubgroupPoint};
use lazy_static::lazy_static;
use rand_core::RngCore;
use serde::{Deserialize, Serialize};

lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: SubgroupPoint =
        crate::crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

#[derive(Debug, PartialEq, Eq, Clone, Serialize, Deserialize)]
pub struct Balance(#[serde(with = "serde_point")] pub SubgroupPoint);

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct BalanceWitness {
    pub value: u64,
    pub unit: String,
    pub blinding: Scalar,
}

impl Balance {
    pub fn from_witness(w: BalanceWitness) -> Self {
        Self(balance(w.value, &w.unit, w.blinding))
    }

    pub fn to_bytes(&self) -> [u8; 32] {
        self.0.to_bytes()
    }
}

impl BalanceWitness {
    pub fn new(value: u64, unit: impl Into<String>, blinding: Scalar) -> Self {
        Self {
            value,
            unit: unit.into(),
            blinding,
        }
    }

    pub fn random(value: u64, unit: impl Into<String>, rng: impl RngCore) -> Self {
        Self::new(value, unit, Scalar::random(rng))
    }

    pub fn unit_point(&self) -> SubgroupPoint {
        unit_point(&self.unit)
    }
}

pub fn unit_point(unit: &str) -> SubgroupPoint {
    crate::crypto::hash_to_curve(unit.as_bytes())
}

pub fn balance(value: u64, unit: &str, blinding: Scalar) -> SubgroupPoint {
    let value_scalar = Scalar::from(value);
    unit_point(unit) * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
}

mod serde_point {
    use super::SubgroupPoint;
    use group::GroupEncoding;
    use serde::de::{self, Visitor};
    use serde::{Deserializer, Serializer};
    use std::fmt;

    // Serialize a SubgroupPoint by converting it to bytes.
    pub fn serialize<S>(point: &SubgroupPoint, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let bytes = point.to_bytes();
        serializer.serialize_bytes(&bytes)
    }

    // Deserialize a SubgroupPoint by converting it from bytes.
    pub fn deserialize<'de, D>(deserializer: D) -> Result<SubgroupPoint, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct BytesVisitor;

        impl<'de> Visitor<'de> for BytesVisitor {
            type Value = SubgroupPoint;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("a valid SubgroupPoint in byte representation")
            }

            fn visit_bytes<E>(self, v: &[u8]) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                let mut bytes = <jubjub::SubgroupPoint as group::GroupEncoding>::Repr::default();
                assert_eq!(bytes.len(), v.len());
                bytes.copy_from_slice(v);

                Ok(SubgroupPoint::from_bytes(&bytes).unwrap())
            }
        }

        deserializer.deserialize_bytes(BytesVisitor)
    }
}
#[cfg(test)]
mod test {

    use crate::test_util::seed_rng;

    use super::*;

    #[test]
    fn test_balance_zero_unitless() {
        // Zero is the same across all units
        let rng = seed_rng(0);
        let r = Scalar::random(rng);
        assert_eq!(
            Balance::from_witness(BalanceWitness::new(0, "NMO", r)),
            Balance::from_witness(BalanceWitness::new(0, "ETH", r)),
        );
    }

    #[test]
    fn test_balance_blinding() {
        // balances are blinded
        let r1 = Scalar::from(12);
        let r2 = Scalar::from(8);
        let a_w = BalanceWitness::new(10, "NMO", r1);
        let b_w = BalanceWitness::new(10, "NMO", r2);
        let a = Balance::from_witness(a_w);
        let b = Balance::from_witness(b_w);
        assert_ne!(a, b);
        assert_eq!(
            a.0 - b.0,
            Balance::from_witness(BalanceWitness::new(0, "NMO", r1 - r2)).0
        );
    }

    #[test]
    fn test_balance_units() {
        // Unit's differentiate between values.
        let r = Scalar::from(1337);
        let nmo = BalanceWitness::new(10, "NMO", r);
        let eth = BalanceWitness::new(10, "ETH", r);
        assert_ne!(Balance::from_witness(nmo), Balance::from_witness(eth));
    }

    #[test]
    fn test_balance_homomorphism() {
        let mut rng = seed_rng(0);
        let r1 = Scalar::random(&mut rng);
        let r2 = Scalar::random(&mut rng);
        let ten = BalanceWitness::new(10, "NMO", 0.into());
        let eight = BalanceWitness::new(8, "NMO", 0.into());
        let two = BalanceWitness::new(2, "NMO", 0.into());

        // Values of same unit are homomorphic
        assert_eq!(
            Balance::from_witness(ten).0 - Balance::from_witness(eight).0,
            Balance::from_witness(two).0
        );

        // Blinding factors are also homomorphic.
        assert_eq!(
            Balance::from_witness(BalanceWitness::new(10, "NMO", r1)).0
                - Balance::from_witness(BalanceWitness::new(10, "NMO", r2)).0,
            Balance::from_witness(BalanceWitness::new(0, "NMO", r1 - r2)).0
        );
    }
}
