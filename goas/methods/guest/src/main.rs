use risc0_zkvm::guest::env;
use std::collections::BTreeMap;

/// Public Inputs:
/// * ptx_root: the root of the partial tx merkle tree of inputs/outputs

/// * in_note_cm: a commitment to the input note
/// * out_note_cm: a commitment to the output note
/// Private inputs:
/// * in_note: a note corresponding to the input commitment
/// * in_ptx_path: the path from a leaf containing the input state commitment in the ptx
/// * out_ptx_path: the path from a leaf containing the output state commitment in the ptx
/// * from: u32, the account to transfer from
/// * to: u32, the account to transfer to
/// * amount: u32, the amount to transfer
///
type Note = BTreeMap<u32, u32>;

fn main() {
    // public input
    let ptx_root: [u8; 32] = env::read();
    let in_ptx_path: Vec<[u8; 32]> = env::read();
    let out_ptx_path: Vec<[u8; 32]> = env::read();

    let in_note_cm: [u8; 32] = env::read();
    let out_note_cm: [u8; 32] = env::read();

    let from: u32 = env::read();
    let to: u32 = env::read();
    let amount: u32 = env::read();

    // private input
    let in_note: Note = env::read();

    // check the note is consistent with the state commitment and is part of the path
    assert_eq!(in_note_cm, calculate_note_hash(&in_note));
    // verify the input state commitment is part of the partial tx
    assert!(verify_path(&ptx_root, &in_ptx_path, &in_note));

    // the note is just the state
    let mut state = in_note.clone();

    // compute transfer
    let from = state.entry(from).or_insert(0);

    *from = from.checked_sub(amount).unwrap();
    *state.entry(to).or_insert(0) += amount;

    // check that the new state is consistent with the output state commitment and it's part of the output
    assert_eq!(calculate_note_hash(&state), out_note_cm);
    let out_note = state;
    assert!(verify_path(&ptx_root, &out_ptx_path, &out_note));
}

fn calculate_note_hash(n: &Note) -> [u8; 32] {
    let mut out = [0u8; 32];
    out[0] = n.len() as u8;
    out
}

fn verify_path(_ptx_root: &[u8; 32], _ptx_path: &[[u8; 32]], _note: &Note) -> bool {
    // for now we just return true
    true
}
