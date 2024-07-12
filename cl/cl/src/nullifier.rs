// The Nullifier is used to detect if a note has
// already been consumed.

// The same nullifier secret may be used across multiple
// notes to allow users to hold fewer secrets. A note
// nonce is used to disambiguate when the same nullifier
// secret is used for multiple notes.
use blake2::{Blake2s256, Digest};
use rand_core::RngCore;
use serde::{Deserialize, Serialize};

// TODO: create a nullifier witness and use it throughout.
// struct NullifierWitness {
//     nf_sk: NullifierSecret,
//     nonce: NullifierNonce
// }

// Maintained privately by note holder
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct NullifierSecret([u8; 16]);

// Nullifier commitment is public information that
// can be provided to anyone wishing to transfer
// you a note
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct NullifierCommitment([u8; 32]);

// To allow users to maintain fewer nullifier secrets, we
// provide a nonce to differentiate notes controlled by the same
// secret. Each note is assigned a unique nullifier nonce.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct NullifierNonce([u8; 16]);

// The nullifier attached to input notes to prove an input has not
// already been spent.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Nullifier([u8; 32]);

impl NullifierSecret {
    pub fn random(mut rng: impl RngCore) -> Self {
        let mut sk = [0u8; 16];
        rng.fill_bytes(&mut sk);
        Self(sk)
    }

    pub fn commit(&self) -> NullifierCommitment {
        let mut hasher = Blake2s256::new();
        hasher.update(b"NOMOS_CL_NULL_COMMIT");
        hasher.update(self.0);

        let commit_bytes: [u8; 32] = hasher.finalize().into();
        NullifierCommitment(commit_bytes)
    }
}

impl NullifierCommitment {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    pub fn hex(&self) -> String {
        hex::encode(self.0)
    }
}

impl NullifierNonce {
    pub fn random(mut rng: impl RngCore) -> Self {
        let mut nonce = [0u8; 16];
        rng.fill_bytes(&mut nonce);
        Self(nonce)
    }

    pub fn as_bytes(&self) -> &[u8; 16] {
        &self.0
    }
}

impl Nullifier {
    pub fn new(sk: NullifierSecret, nonce: NullifierNonce) -> Self {
        let mut hasher = Blake2s256::new();
        hasher.update(b"NOMOS_CL_NULLIFIER");
        hasher.update(sk.0);
        hasher.update(nonce.0);

        let nf_bytes: [u8; 32] = hasher.finalize().into();
        Self(nf_bytes)
    }

    pub(crate) fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_nullifier_commitment_vectors() {
        assert_eq!(
            NullifierSecret([0u8; 16]).commit().hex(),
            "384318f9864fe57647bac344e2afdc500a672dedb29d2dc63b004e940e4b382a"
        );
        assert_eq!(
            NullifierSecret([1u8; 16]).commit().hex(),
            "0fd667e6bb39fbdc35d6265726154b839638ea90bcf4e736953ccf27ca5f870b"
        );
        assert_eq!(
            NullifierSecret([u8::MAX; 16]).commit().hex(),
            "1cb78e487eb0b3116389311fdde84cd3f619a4d7f487b29bf5a002eed3784d75"
        );
    }

    #[test]
    fn test_nullifier_same_sk_different_nonce() {
        let mut rng = rand::thread_rng();
        let sk = NullifierSecret::random(&mut rng);
        let nonce_1 = NullifierNonce::random(&mut rng);
        let nonce_2 = NullifierNonce::random(&mut rng);
        let nf_1 = Nullifier::new(sk, nonce_1);
        let nf_2 = Nullifier::new(sk, nonce_2);

        assert_ne!(nf_1, nf_2);
    }
}
