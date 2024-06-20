use blake2::{Blake2s256, Digest};
use risc0_zkvm::guest::env;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// Public Inputs:
/// * ptx_root: the root of the partial tx merkle tree of inputs/outputs
/// Private inputs:
/// TODO

// state of the zone
type State = BTreeMap<u32, u32>;
// list of all inputs that were executed up to this point
type Journal = Vec<Input>;

#[derive(Clone, Serialize, Deserialize)]
struct Note {
    state_cm: [u8; 32],
    journal_cm: [u8; 32],
    zone_input: Input,
}

#[derive(Clone, Copy, Serialize, Deserialize)]
enum Input {
    Transfer { from: u32, to: u32, amount: u32 },
}

/// State transition function
fn stf(mut state: State, input: Input) -> State {
    match input {
        Input::Transfer { from, to, amount } => {
            // compute transfer
            let from = state.entry(from).or_insert(0);
            *from = from.checked_sub(amount).unwrap();
            *state.entry(to).or_insert(0) += amount;
        }
    }
    state
}

/// Glue the zone and the cl together, specifically, it verifies the note requesting
/// a transfer is included as part of the same transaction in the cl
fn verify_ptx_inputs(ptx_root: [u8; 32], ptx_path: &[[u8; 32]], note: &Note) {
    assert!(verify_path(&ptx_root, &ptx_path, &note));
}

/// Glue the zone and the cl together, specifically, it verifies an output note
/// containing the zone state is included as part of the same transaction in the cl
/// (this is done in the death condition to disallow burning)
fn verify_ptx_output(ptx_root: [u8; 32], ptx_path: &[[u8; 32]], note: &Note) {
    assert!(verify_path(&ptx_root, &ptx_path, &note));
}

fn execute(
    ptx_root: [u8; 32],
    ptx_path: Vec<[u8; 32]>,
    note: Note,
    state: State,
    mut journal: Journal,
) -> (State, Journal) {
    // verify ptx/cl preconditions
    verify_ptx_inputs(ptx_root, &ptx_path, &note);

    // check the commitments match the actual data
    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);
    assert_eq!(state_cm, note.state_cm);
    assert_eq!(journal_cm, note.journal_cm);

    // then run the state transition function
    let input = note.zone_input;
    let state = stf(state, input);
    journal.push(input);

    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);

    // verifying ptx/cl postconditions
    verify_ptx_outputs(ptx_root, &ptx_path, out_note);
    // output the new state and the execution receipt
    (state, journal)
}

fn main() {
    // public input
    let ptx_root: [u8; 32] = env::read();

    // private input
    let in_ptx_path: Vec<[u8; 32]> = env::read();
    let out_ptx_path: Vec<[u8; 32]> = env::read();
    let note: Note = env::read();
    let state: State = env::read();
    let journal: Journal = env::read();

    execute(ptx_root, in_ptx_path, out_ptx_path, note, state, journal);
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
