use blake2::{Blake2s256, Digest};
use risc0_zkvm::guest::env;
use common::*;
use cl::merkle;
use cl::note::NoteWitness

/// Public Inputs:
/// * ptx_root: the root of the partial tx merkle tree of inputs/outputs
/// Private inputs:
/// TODO

/// Glue the zone and the cl together, specifically, it verifies the note requesting
/// a transfer is included as part of the same transaction in the cl
fn verify_ptx_inputs(ptx_root: [u8; 32], ptx_path: &[[u8; 32]], note: &Note) {
    assert!(verify_path(&ptx_root, &ptx_path, &note));
}

/// Glue the zone and the cl together, specifically, it verifies an output note
/// containing the zone state is included as part of the same transaction in the cl
/// (this is done in the death condition to disallow burning)
fn verify_ptx_outputs(ptx_root: [u8; 32], ptx_path: &[[u8; 32]], note: &Note) {
    assert!(verify_path(&ptx_root, &ptx_path, &note));
}

fn execute(
    ptx_root: [u8; 32],
    input_root: [u8; 32],
    output_root: [u8; 32],
    in_ptx_path: Vec<merkle::PathNode>,
    out_ptx_path: Vec<merkle::PathNode>,
    in_note: NoteWitness,
    out_note: NotWitness,
    input: Input,
    state: State,
    mut journal: Journal,
) {
    // verify ptx/cl preconditions

    assert_eq!(ptx_root, merkle::node(input_root, output_root));
    assert!(merkle::verify_path(in_note.commit().0, in_ptx_path, input_root));

    // check the commitments match the actual data
    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);
    let state_root = merkle::node(state_cm, journal_cm);
    assert_eq!(state_root, in_note.state);

    // then run the state transition function
    let state = stf(state, input);
    journal.push(input);

    // verifying ptx/cl postconditions

    let out_state_cm = calculate_state_hash(&state);
    let out_journal_cm = calculate_journal_hash(&journal);
    let out_state_root = merkle::node(out_state_cm, out_journal_cm);
    // TODO: verify death constraints are propagated
    assert_eq!(out_state_root, out_note.state);
    assert!(merkle::verify_path(out_note.commit().0, out_ptx_path, output_root));
}

fn main() {
    // public input
    let ptx_root: [u8; 32] = env::read();

    // private input
    let input_root: [u8; 32] = env::read();
    let output_root: [u8; 32] = env::read();
    let in_ptx_path: Vec<merkle::PathNode> = env::read();
    let out_ptx_path: Vec<merkle::PathNode> = env::read();
    let in_note: NoteWitness = env::read();
    let out_note: NoteWitness = env::read();
    let input: Input = env::read()
    let state: State = env::read();
    let journal: Journal = env::read();

    execute(ptx_root, input_root, output_root, in_ptx_path, out_ptx_path, in_note, out_note, input, state, journal);
}

fn calculate_state_hash(state: &State) -> [u8; 32] {
    let bytes = bincode::serialize(state).unwrap();
    Blake2s256::digest(&bytes).into()
}

fn calculate_journal_hash(journal: &Journal) -> [u8; 32] {
    let bytes = bincode::serialize(journal).unwrap();
    Blake2s256::digest(&bytes).into()
}

fn verify_path(_ptx_root: &[u8; 32], _ptx_path: &[[u8; 32]], _note: &Note) -> bool {
    // for now we just return true
    true
}
