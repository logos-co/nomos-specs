use rand_core::SeedableRng;

pub fn seed_rng(seed: u64) -> impl rand_core::RngCore {
    let mut bytes = [0u8; 32];
    (&mut bytes[..8]).copy_from_slice(&seed.to_le_bytes());
    rand_chacha::ChaCha12Rng::from_seed(bytes)
}
