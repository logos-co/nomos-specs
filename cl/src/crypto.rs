use blake2::Blake2b512;
use curve25519_dalek::ristretto::RistrettoPoint;

pub fn hash_to_curve(bytes: &[u8]) -> RistrettoPoint {
    RistrettoPoint::hash_from_bytes::<Blake2b512>(bytes)
}
