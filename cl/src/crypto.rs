use k256::{Secp256k1, ProjectivePoint,  elliptic_curve::{
        hash2curve::{GroupDigest, ExpandMsgXmd},
},sha2::Sha256
};

pub fn hash_to_curve(bytes: &[u8]) -> ProjectivePoint {
    Secp256k1::hash_from_bytes::<ExpandMsgXmd<Sha256>>(&[bytes], &[b"NOMOS_HASH_TO_CURVE"]).unwrap()
}
