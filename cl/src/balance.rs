use lazy_static::lazy_static;
use rand_core::RngCore;
use serde::{Deserialize, Serialize};
use k256::{
    elliptic_curve::{
        group::GroupEncoding, Field
    },
    ProjectivePoint, Scalar, AffinePoint
};


lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: ProjectivePoint =
        crate::crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

#[derive(Debug, PartialEq, Eq, Clone, Serialize, Deserialize)]
pub struct Balance(pub AffinePoint);

#[derive(Debug, PartialEq, Eq, Clone, Serialize, Deserialize)]
pub struct BalanceWitness {
    pub value: u64,
    pub unit: String,
    pub blinding: Scalar,
}

impl Balance {
    pub fn to_bytes(&self) -> [u8; 33] {
        self.0.to_bytes().into()
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

    pub fn commit(&self) -> Balance {
        Balance(balance(self.value, &self.unit, self.blinding).into())
    }

    pub fn unit_point(&self) -> ProjectivePoint {
        unit_point(&self.unit)
    }
}

pub fn unit_point(unit: &str) -> ProjectivePoint {
    crate::crypto::hash_to_curve(unit.as_bytes())
}

pub fn balance(value: u64, unit: &str, blinding: Scalar) -> ProjectivePoint {
    let value_scalar = Scalar::from(value);
    unit_point(unit) * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
}

// mod serde_scalar {
//     use super::Scalar;
//     use serde::de::{self, Visitor};
//     use serde::{Deserializer, Serializer};
//     use std::fmt;

//     // Serialize a SubgroupPoint by converting it to bytes.
//     pub fn serialize<S>(scalar: &Scalar, serializer: S) -> Result<S::Ok, S::Error>
//     where
//         S: Serializer,
//     {
//         let bytes = scalar.to_bytes();
//         serializer.serialize_bytes(&bytes)
//     }

//     // Deserialize a SubgroupPoint by converting it from bytes.
//     pub fn deserialize<'de, D>(deserializer: D) -> Result<Scalar, D::Error>
//     where
//         D: Deserializer<'de>,
//     {
//         struct BytesVisitor;

//         impl<'de> Visitor<'de> for BytesVisitor {
//             type Value = Scalar;

//             fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
//                 formatter.write_str("a valid Scalar in byte representation")
//             }

//             fn visit_bytes<E>(self, v: &[u8]) -> Result<Self::Value, E>
//             where
//                 E: de::Error,
//             {
//                 let mut bytes = <jubjub::SubgroupPoint as group::GroupEncoding>::Repr::default();
//                 assert_eq!(bytes.len(), v.len());
//                 bytes.copy_from_slice(v);

//                 Ok(Scalar::from_bytes(&bytes).unwrap())
//             }
//         }

//         deserializer.deserialize_bytes(BytesVisitor)
//     }
// }

// mod serde_point {
//     use super::SubgroupPoint;
//     use group::GroupEncoding;
//     use serde::de::{self, Visitor};
//     use serde::{Deserializer, Serializer};
//     use std::fmt;

//     // Serialize a SubgroupPoint by converting it to bytes.
//     pub fn serialize<S>(point: &SubgroupPoint, serializer: S) -> Result<S::Ok, S::Error>
//     where
//         S: Serializer,
//     {
//         let bytes = point.to_bytes();
//         serializer.serialize_bytes(&bytes)
//     }

//     // Deserialize a SubgroupPoint by converting it from bytes.
//     pub fn deserialize<'de, D>(deserializer: D) -> Result<SubgroupPoint, D::Error>
//     where
//         D: Deserializer<'de>,
//     {
//         struct BytesVisitor;

//         impl<'de> Visitor<'de> for BytesVisitor {
//             type Value = SubgroupPoint;

//             fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
//                 formatter.write_str("a valid SubgroupPoint in byte representation")
//             }

//             fn visit_bytes<E>(self, v: &[u8]) -> Result<Self::Value, E>
//             where
//                 E: de::Error,
//             {
//                 let mut bytes = <jubjub::SubgroupPoint as group::GroupEncoding>::Repr::default();
//                 assert_eq!(bytes.len(), v.len());
//                 bytes.copy_from_slice(v);

//                 Ok(SubgroupPoint::from_bytes(&bytes).unwrap())
//             }
//         }

//         deserializer.deserialize_bytes(BytesVisitor)
//     }
// }

#[cfg(test)]
mod test {

    use crate::test_util::seed_rng;
    use k256::elliptic_curve::group::prime::PrimeCurveAffine;

    use super::*;

    #[test]
    fn test_balance_zero_unitless() {
        // Zero is the same across all units
        let rng = seed_rng(0);
        let r = Scalar::random(rng);
        assert_eq!(
            BalanceWitness::new(0, "NMO", r).commit(),
            BalanceWitness::new(0, "ETH", r).commit(),
        );
    }

    #[test]
    fn test_balance_blinding() {
        // balances are blinded
        let r1 = Scalar::from(12u32);
        let r2 = Scalar::from(8u32);
        let a_w = BalanceWitness::new(10, "NMO", r1);
        let b_w = BalanceWitness::new(10, "NMO", r2);
        let a = a_w.commit();
        let b = b_w.commit();
        assert_ne!(a, b);
        assert_eq!(a.0.to_curve() - b.0.to_curve(), BalanceWitness::new(0, "NMO", r1 - r2).commit().0.to_curve());
    }

    #[test]
    fn test_balance_units() {
        // Unit's differentiate between values.
        let r = Scalar::from(1337u32);
        let nmo = BalanceWitness::new(10, "NMO", r);
        let eth = BalanceWitness::new(10, "ETH", r);
        assert_ne!(nmo.commit(), eth.commit());
    }

    #[test]
    fn test_balance_homomorphism() {
        let mut rng = seed_rng(0);
        let r1 = Scalar::random(&mut rng);
        let r2 = Scalar::random(&mut rng);
        let ten = BalanceWitness::new(10, "NMO", 0u32.into());
        let eight = BalanceWitness::new(8, "NMO", 0u32.into());
        let two = BalanceWitness::new(2, "NMO", 0u32.into());

        // Values of same unit are homomorphic
        assert_eq!(ten.commit().0.to_curve() - eight.commit().0.to_curve(), two.commit().0.to_curve());

        // Blinding factors are also homomorphic.
        assert_eq!(
            BalanceWitness::new(10, "NMO", r1).commit().0.to_curve()
                - BalanceWitness::new(10, "NMO", r2).commit().0.to_curve(),
            BalanceWitness::new(0, "NMO", r1 - r2).commit().0.to_curve()
        );
    }
}
