use sha2::Sha512;
use curve25519_dalek::ristretto::RistrettoPoint;

pub fn hash_to_curve(bytes: &[u8]) -> RistrettoPoint {
    RistrettoPoint::hash_from_bytes::<Sha512>(bytes)
}
