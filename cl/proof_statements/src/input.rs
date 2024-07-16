use serde::{Deserialize, Serialize};

/// for public inputs `nf` (nullifier), `root_cm` (root of merkle tree over commitment set) and `death_cm` (commitment to death constraint).
/// the prover has knowledge of `output = (note, nf_pk, nonce)`, `nf` and `path` s.t. that the following constraints hold
/// 0. nf_pk = hash(nf_sk)
/// 1. nf = hash(nonce||nf_sk)
/// 2. note_cm = output_commitment(output)
/// 3. verify_merkle_path(note_cm, root, path)
/// 4. death_cm = death_commitment(note.death_constraint)

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct InputPublic {
    pub cm_root: [u8; 32],
    pub input: cl::Input,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InputPrivate {
    pub input: cl::InputWitness,
    pub cm_path: Vec<cl::merkle::PathNode>,
}
