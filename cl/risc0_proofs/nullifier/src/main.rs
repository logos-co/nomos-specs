/// Nullifier Proof
///
/// Our goal: prove the nullifier nf was derived from a note that had previously been committed to.
///
/// More formally, nullifier statement says:
/// for public input `nf` (nullifier) and `root_cm` (root of merkle tree over commitment set).
/// the prover has knowledge of `output = (note, nf_pk, nonce)`, `nf` and `path` s.t. that the following constraints hold
/// 0. nf_pk = hash(nf_sk)
/// 1. nf = hash(nonce||nf_sk)
/// 2. note_cm = output_commitment(output)
/// 3. verify_merkle_path(note_cm, root, path)
use cl::merkle;
use cl::nullifier::Nullifier;
use proof_statements::nullifier::{NullifierPrivate, NullifierPublic};
use risc0_zkvm::guest::env;

fn main() {
    let secret: NullifierPrivate = env::read();
    assert_eq!(secret.output.nf_pk, secret.nf_sk.commit());

    let cm_out = secret.output.commit_note();
    let cm_leaf = merkle::leaf(cm_out.as_bytes());
    let cm_root = merkle::path_root(cm_leaf, &secret.cm_path);

    let nf = Nullifier::new(secret.nf_sk, secret.output.nonce);

    env::commit(&NullifierPublic { cm_root, nf });
}
