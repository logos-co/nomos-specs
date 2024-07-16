use curve25519_dalek::{ristretto::RistrettoPoint, traits::VartimeMultiscalarMul, Scalar};
use lazy_static::lazy_static;
use rand_core::CryptoRngCore;
use serde::{Deserialize, Serialize};
lazy_static! {
    // Precompute of ``
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: RistrettoPoint = crate::crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

#[derive(Debug, PartialEq, Eq, Clone, Copy, Serialize, Deserialize)]
pub struct Balance(pub RistrettoPoint);

#[derive(Debug, PartialEq, Eq, Clone, Copy, Serialize, Deserialize)]
pub struct BalanceWitness {
    pub value: u64,
    pub unit: RistrettoPoint,
    pub blinding: Scalar,
}

impl Balance {
    pub fn to_bytes(&self) -> [u8; 32] {
        self.0.compress().to_bytes().into()
    }
}

impl BalanceWitness {
    pub fn new(value: u64, unit: impl Into<String>, blinding: Scalar) -> Self {
        Self {
            value,
            unit: unit_point(&unit.into()),
            blinding,
        }
    }

    pub fn random(value: u64, unit: impl Into<String>, mut rng: impl CryptoRngCore) -> Self {
        Self::new(value, unit, Scalar::random(&mut rng))
    }

    pub fn commit(&self) -> Balance {
        Balance(balance(self.value, self.unit, self.blinding))
    }
}

pub fn unit_point(unit: &str) -> RistrettoPoint {
    crate::crypto::hash_to_curve(unit.as_bytes())
}

pub fn balance(value: u64, unit: RistrettoPoint, blinding: Scalar) -> RistrettoPoint {
    let value_scalar = Scalar::from(value);
    // can vartime leak the number of cycles through the stark proof?
    RistrettoPoint::vartime_multiscalar_mul(
        &[value_scalar, blinding],
        &[unit, *PEDERSON_COMMITMENT_BLINDING_POINT],
    )
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

    use super::*;

    #[test]
    fn test_pederson_blinding_point_pre_compute() {
        // use k256::elliptic_curve::group::GroupEncoding;
        // println!("{:?}", <[u8;33]>::from((*PEDERSON_COMMITMENT_BLINDING_POINT).to_bytes()));

        assert_eq!(
            *PEDERSON_COMMITMENT_BLINDING_POINT,
            crate::crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING")
        );
    }

    #[test]
    fn test_balance_zero_unitless() {
        // Zero is the same across all units
        let mut rng = rand::thread_rng();
        let r = Scalar::random(&mut rng);
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
        assert_eq!(a.0 - b.0, BalanceWitness::new(0, "NMO", r1 - r2).commit().0);
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
        let mut rng = rand::thread_rng();
        let r1 = Scalar::random(&mut rng);
        let r2 = Scalar::random(&mut rng);
        let ten = BalanceWitness::new(10, "NMO", 0u32.into());
        let eight = BalanceWitness::new(8, "NMO", 0u32.into());
        let two = BalanceWitness::new(2, "NMO", 0u32.into());

        // Values of same unit are homomorphic
        assert_eq!(ten.commit().0 - eight.commit().0, two.commit().0);

        // Blinding factors are also homomorphic.
        assert_eq!(
            BalanceWitness::new(10, "NMO", r1).commit().0
                - BalanceWitness::new(10, "NMO", r2).commit().0,
            BalanceWitness::new(0, "NMO", r1 - r2).commit().0
        );
    }
}
