use jubjub::ExtendedPoint;

use crate::input::{Input, InputProof};
use crate::output::{Output, OutputProof};

pub struct PartialTx {
    inputs: Vec<(Input, InputProof)>,
    outputs: Vec<(Output, OutputProof)>,
}

impl PartialTx {
    pub fn verify(&self) -> bool {
        self.inputs.iter().all(|(i, p)| i.verify(p))
            && self.outputs.iter().all(|(o, p)| o.verify(p))
    }

    pub fn balance(&self) -> ExtendedPoint {
        let in_sum = self
            .inputs
            .iter()
            .map(|(i, _)| i.balance)
            .sum::<ExtendedPoint>();
        let out_sum = self
            .outputs
            .iter()
            .map(|(o, _)| o.balance)
            .sum::<ExtendedPoint>();

        in_sum - out_sum
    }
}
