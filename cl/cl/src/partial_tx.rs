use rand_core::RngCore;
// use risc0_groth16::ProofJson;
use curve25519_dalek::ristretto::RistrettoPoint;
use serde::{Deserialize, Serialize};

use crate::input::{Input, InputWitness};
use crate::merkle;
use crate::output::{Output, OutputWitness};

const MAX_INPUTS: usize = 8;
const MAX_OUTPUTS: usize = 8;

/// The partial transaction commitment couples an input to a partial transaction.
/// Prevents partial tx unbundling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct PtxRoot(pub [u8; 32]);

impl PtxRoot {
    pub fn random(mut rng: impl RngCore) -> Self {
        let mut sk = [0u8; 32];
        rng.fill_bytes(&mut sk);
        Self(sk)
    }

    pub fn hex(&self) -> String {
        hex::encode(self.0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialTx {
    pub inputs: Vec<Input>,
    pub outputs: Vec<Output>,
}

#[derive(Debug, Clone)]
pub struct PartialTxWitness {
    pub inputs: Vec<InputWitness>,
    pub outputs: Vec<OutputWitness>,
}

impl PartialTx {
    pub fn from_witness(w: PartialTxWitness) -> Self {
        Self {
            inputs: Vec::from_iter(w.inputs.iter().map(InputWitness::commit)),
            outputs: Vec::from_iter(w.outputs.iter().map(OutputWitness::commit)),
        }
    }

    pub fn input_root(&self) -> [u8; 32] {
        let input_bytes =
            Vec::from_iter(self.inputs.iter().map(Input::to_bytes).map(Vec::from_iter));
        let input_merkle_leaves = merkle::padded_leaves(&input_bytes);
        merkle::root::<MAX_INPUTS>(input_merkle_leaves)
    }

    pub fn output_root(&self) -> [u8; 32] {
        let output_bytes = Vec::from_iter(
            self.outputs
                .iter()
                .map(Output::to_bytes)
                .map(Vec::from_iter),
        );
        let output_merkle_leaves = merkle::padded_leaves(&output_bytes);
        merkle::root::<MAX_OUTPUTS>(output_merkle_leaves)
    }

    pub fn input_merkle_path(&self, idx: usize) -> Vec<merkle::PathNode> {
        let input_bytes =
            Vec::from_iter(self.inputs.iter().map(Input::to_bytes).map(Vec::from_iter));
        let input_merkle_leaves = merkle::padded_leaves::<MAX_INPUTS>(&input_bytes);
        merkle::path(input_merkle_leaves, idx)
    }

    pub fn output_merkle_path(&self, idx: usize) -> Vec<merkle::PathNode> {
        let output_bytes = Vec::from_iter(
            self.outputs
                .iter()
                .map(Output::to_bytes)
                .map(Vec::from_iter),
        );
        let output_merkle_leaves = merkle::padded_leaves::<MAX_OUTPUTS>(&output_bytes);
        merkle::path(output_merkle_leaves, idx)
    }

    pub fn root(&self) -> PtxRoot {
        let input_root = self.input_root();
        let output_root = self.output_root();
        let root = merkle::node(input_root, output_root);
        PtxRoot(root)
    }

    pub fn balance(&self) -> RistrettoPoint {
        let in_sum: RistrettoPoint = self.inputs.iter().map(|i| i.balance.0).sum();
        let out_sum: RistrettoPoint = self.outputs.iter().map(|o| o.balance.0).sum();

        out_sum - in_sum
    }
}

#[cfg(test)]
mod test {

    use crate::{crypto::hash_to_curve, note::NoteWitness, nullifier::NullifierSecret};

    use super::*;

    #[test]
    fn test_partial_tx_balance() {
        let mut rng = rand::thread_rng();

        let nmo_10 =
            InputWitness::random(NoteWitness::new(10, "NMO", [0u8; 32], &mut rng), &mut rng);
        let eth_23 =
            InputWitness::random(NoteWitness::new(23, "ETH", [0u8; 32], &mut rng), &mut rng);
        let crv_4840 = OutputWitness::random(
            NoteWitness::new(4840, "CRV", [0u8; 32], &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        let ptx_witness = PartialTxWitness {
            inputs: vec![nmo_10.clone(), eth_23.clone()],
            outputs: vec![crv_4840.clone()],
        };

        let ptx = PartialTx::from_witness(ptx_witness.clone());

        assert_eq!(
            ptx.balance(),
            crate::balance::balance(4840, hash_to_curve(b"CRV"), crv_4840.note.balance.blinding)
                - (crate::balance::balance(
                    10,
                    hash_to_curve(b"NMO"),
                    nmo_10.note.balance.blinding
                ) + crate::balance::balance(
                    23,
                    hash_to_curve(b"ETH"),
                    eth_23.note.balance.blinding
                ))
        );
    }
}
