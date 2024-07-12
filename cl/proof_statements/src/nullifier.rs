use serde::{Deserialize, Serialize};

/// for public input `nf` (nullifier) and `root_cm` (root of merkle tree over commitment set).
/// the prover has knowledge of `output = (note, nf_pk, nonce)`, `nf` and `path` s.t. that the following constraints hold
/// 0. nf_pk = hash(nf_sk)
/// 1. nf = hash(nonce||nf_sk)
/// 2. note_cm = output_commitment(output)
/// 3. verify_merkle_path(note_cm, root, path)

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NullifierPublic {
    pub cm_root: [u8; 32],
    pub nf: cl::Nullifier,
    // TODO: we need a way to link this statement to a particular input. i.e. prove that the nullifier is actually derived from the input note.
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NullifierPrivate {
    pub nf_sk: cl::NullifierSecret,
    pub output: cl::OutputWitness,
    pub cm_path: Vec<cl::merkle::PathNode>,
}
