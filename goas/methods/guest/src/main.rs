use blake2::{Blake2s256, Digest};
use risc0_zkvm::guest::env;
use common::*;

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
    in_ptx_path: Vec<[u8; 32]>,
    out_ptx_path: Vec<[u8; 32]>,
    in_note: Note,
    out_note: Note,
    state: State,
    mut journal: Journal,
) -> (State, Journal) {
    // verify ptx/cl preconditions
    verify_ptx_inputs(ptx_root, &in_ptx_path, &in_note);

    // check the commitments match the actual data
    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);
    assert_eq!(state_cm, in_note.state_cm);
    assert_eq!(journal_cm, in_note.journal_cm);

    // then run the state transition function
    let input = in_note.zone_input;
    let state = stf(state, input);
    journal.push(input);

    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);

    // TODO: verify death constraints are propagated
    assert_eq!(state_cm, out_note.state_cm);
    assert_eq!(journal_cm, out_note.journal_cm);

    // verifying ptx/cl postconditions
    verify_ptx_outputs(ptx_root, &out_ptx_path, &out_note);
    // output the new state and the execution receipt
    (state, journal)
}

fn main() {
    // public input
    let ptx_root: [u8; 32] = env::read();

    // private input
    let in_ptx_path: Vec<[u8; 32]> = env::read();
    let out_ptx_path: Vec<[u8; 32]> = env::read();
    let in_note: Note = env::read();
    let out_note: Note = env::read();
    let state: State = env::read();
    let journal: Journal = env::read();

    execute(ptx_root, in_ptx_path, out_ptx_path, in_note, out_note, state, journal);
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
