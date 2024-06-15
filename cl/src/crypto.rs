use blake2::{Blake2s256, Digest};
use group::Group;
use jubjub::SubgroupPoint;
use rand_chacha::ChaCha20Rng;
use rand_core::SeedableRng;

pub fn hash_to_curve(bytes: &[u8]) -> SubgroupPoint {
    let mut hasher = Blake2s256::new();
    hasher.update(b"NOMOS_HASH_TO_CURVE");
    hasher.update(bytes);
    let seed: [u8; 32] = hasher.finalize().into();
    SubgroupPoint::random(ChaCha20Rng::from_seed(seed))
}
