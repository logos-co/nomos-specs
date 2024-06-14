use jubjub::{ExtendedPoint, Scalar};
use lazy_static::lazy_static;

lazy_static! {
    static ref PEDERSON_COMMITMENT_BLINDING_POINT: ExtendedPoint =
        crate::crypto::hash_to_curve(b"NOMOS_CL_PEDERSON_COMMITMENT_BLINDING");
}

pub fn unit_point(unit: &str) -> ExtendedPoint {
    crate::crypto::hash_to_curve(unit.as_bytes())
}

pub fn balance(value: u64, unit: &str, blinding: Scalar) -> ExtendedPoint {
    let value_scalar = Scalar::from(value);
    unit_point(unit) * value_scalar + *PEDERSON_COMMITMENT_BLINDING_POINT * blinding
}
