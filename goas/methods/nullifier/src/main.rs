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
use cl::nullifier::{Nullifier, NullifierSecret};
use cl::output::OutputWitness;
use risc0_zkvm::guest::env;

fn execute(
    // public
    cm_root: [u8; 32],
    nf: Nullifier,
    // private
    nf_sk: NullifierSecret,
    output: OutputWitness,
    cm_path: Vec<merkle::PathNode>,
) {
    eprintln!("start exec: {}", env::cycle_count());

    assert_eq!(output.nf_pk, nf_sk.commit());
    eprintln!("output nullifier: {}", env::cycle_count());

    assert_eq!(nf, Nullifier::new(nf_sk, output.nonce));
    eprintln!("nullifier: {}", env::cycle_count());

    let cm_out = output.commit_note();
    eprintln!("out_cm: {}", env::cycle_count());

    assert!(merkle::verify_path(
        merkle::leaf(cm_out.as_bytes()),
        &cm_path,
        cm_root
    ));
    eprintln!("nullifier merkle path: {}", env::cycle_count());
}

fn main() {
    // public input
    let cm_root: [u8; 32] = env::read();
    let nf: Nullifier = env::read();

    // private input
    let nf_sk: NullifierSecret = env::read();
    let output: OutputWitness = env::read();
    let cm_path: Vec<merkle::PathNode> = env::read();

    eprintln!("parse input: {}", env::cycle_count());
    execute(cm_root, nf, nf_sk, output, cm_path);
}
