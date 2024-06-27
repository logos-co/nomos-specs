use serde::{Serialize, Deserialize};
use std::collections::BTreeMap;

// state of the zone
pub type State = BTreeMap<u32, u32>;
// list of all inputs that were executed up to this point
pub type Journal = Vec<Input>;

#[derive(Clone, Copy, Serialize, Deserialize)]
pub enum Input {
    Transfer { from: u32, to: u32, amount: u32 },
    None,
}


/// State transition function of the zone
pub fn stf(mut state: State, input: Input) -> State {
    match input {
        Input::Transfer { from, to, amount } => {
            // compute transfer
            let from = state.entry(from).or_insert(0);
            *from = from.checked_sub(amount).unwrap();
            *state.entry(to).or_insert(0) += amount;
        }
        Input::None => {}
    }
    state
}
