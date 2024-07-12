use blake2::{Blake2s256, Digest};
use cl::input::InputWitness;
use cl::merkle;
use cl::output::OutputWitness;
use common::*;
use risc0_zkvm::guest::env;

/// Public Inputs:
/// * ptx_root: the root of the partial tx merkle tree of inputs/outputs
/// Private inputs:
/// TODO

fn execute(
    ptx_root: [u8; 32],
    input_root: [u8; 32],
    output_root: [u8; 32],
    in_ptx_path: Vec<merkle::PathNode>,
    out_ptx_path: Vec<merkle::PathNode>,
    in_note: InputWitness,
    out_note: OutputWitness,
    input: Input,
    state: State,
    mut journal: Journal,
) {
    // verify ptx/cl preconditions
    eprintln!("start exec: {}", env::cycle_count());
    assert_eq!(ptx_root, merkle::node(input_root, output_root));
    eprintln!("ptx_root: {}", env::cycle_count());

    // Glue the zone and the cl together, specifically, it verifies the note requesting
    // a transfer is included as part of the same transaction in the cl
    let in_comm = in_note.commit().to_bytes();
    eprintln!("input comm: {}", env::cycle_count());

    assert_eq!(
        merkle::path_root(merkle::leaf(&in_comm), &in_ptx_path),
        input_root
    );
    eprintln!("input merkle path: {}", env::cycle_count());

    // check the commitments match the actual data
    let state_cm = calculate_state_hash(&state);
    let journal_cm = calculate_journal_hash(&journal);
    let state_root = merkle::node(state_cm, journal_cm);
    assert_eq!(state_root, in_note.note.state);
    eprintln!("input state root: {}", env::cycle_count());

    // then run the state transition function
    let state = stf(state, input);
    journal.push(input);
    eprintln!("stf: {}", env::cycle_count());

    // verifying ptx/cl postconditions

    let out_state_cm = calculate_state_hash(&state);
    let out_journal_cm = calculate_journal_hash(&journal);
    let out_state_root = merkle::node(out_state_cm, out_journal_cm);
    // TODO: verify death constraints are propagated
    assert_eq!(out_state_root, out_note.note.state);
    eprintln!("out state root: {}", env::cycle_count());

    // Glue the zone and the cl together, specifically, it verifies an output note
    // containing the zone state is included as part of the same transaction in the cl
    // (this is done in the death condition to disallow burning)
    let out_comm = out_note.commit().to_bytes();
    eprintln!("output comm: {}", env::cycle_count());

    assert_eq!(
        merkle::path_root(merkle::leaf(&out_comm), &out_ptx_path),
        output_root
    );
    eprintln!("out merkle proof: {}", env::cycle_count());
}

fn main() {
    // public input
    let ptx_root: [u8; 32] = env::read();

    // private input
    let input_root: [u8; 32] = env::read();
    let output_root: [u8; 32] = env::read();
    let in_ptx_path: Vec<merkle::PathNode> = env::read();
    let out_ptx_path: Vec<merkle::PathNode> = env::read();
    let in_note: InputWitness = env::read();
    let out_note: OutputWitness = env::read();
    let input: Input = env::read();
    let state: State = env::read();
    let journal: Journal = env::read();

    eprintln!("parse input: {}", env::cycle_count());
    execute(
        ptx_root,
        input_root,
        output_root,
        in_ptx_path,
        out_ptx_path,
        in_note,
        out_note,
        input,
        state,
        journal,
    );
}

fn calculate_state_hash(state: &State) -> [u8; 32] {
    let bytes = bincode::serialize(state).unwrap();
    Blake2s256::digest(&bytes).into()
}

fn calculate_journal_hash(journal: &Journal) -> [u8; 32] {
    let bytes = bincode::serialize(journal).unwrap();
    Blake2s256::digest(&bytes).into()
}
