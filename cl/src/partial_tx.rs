use std::collections::BTreeSet;

use jubjub::SubgroupPoint;
use rand_core::RngCore;
use risc0_groth16::ProofJson;
use serde::{Deserialize, Serialize};

use crate::error::Error;
use crate::input::{Input, InputProof, InputWitness};
use crate::merkle;
use crate::output::{Output, OutputProof, OutputWitness};

const MAX_INPUTS: usize = 32;
const MAX_OUTPUTS: usize = 32;

/// The partial transaction commitment couples an input to a partial transaction.
/// Prevents partial tx unbundling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct PtxRoot([u8; 32]);

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

#[derive(Debug)]
pub struct PartialTxProof {
    pub inputs: Vec<InputProof>,
    pub outputs: Vec<OutputProof>,
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

    pub fn prove(
        &self,
        w: PartialTxWitness,
        death_proofs: Vec<Vec<u8>>,
    ) -> Result<PartialTxProof, Error> {
        if bincode::serialize(&Self::from_witness(w.clone())).unwrap()
            != bincode::serialize(&self).unwrap()
        {
            return Err(Error::ProofFailed);
        }
        let input_note_comms = BTreeSet::from_iter(self.inputs.iter().map(|i| i.note_comm));
        let output_note_comms = BTreeSet::from_iter(self.outputs.iter().map(|o| o.note_comm));

        if input_note_comms.len() != self.inputs.len()
            || output_note_comms.len() != self.outputs.len()
        {
            return Err(Error::ProofFailed);
        }

        let ptx_root = self.root();

        let input_proofs: Vec<InputProof> = Result::from_iter(
            self.inputs
                .iter()
                .zip(&w.inputs)
                .zip(death_proofs.into_iter())
                .map(|((i, i_w), death_p)| i.prove(i_w, ptx_root, death_p)),
        )?;

        let output_proofs: Vec<OutputProof> = Result::from_iter(
            self.outputs
                .iter()
                .zip(&w.outputs)
                .map(|(o, o_w)| o.prove(o_w)),
        )?;

        Ok(PartialTxProof {
            inputs: input_proofs,
            outputs: output_proofs,
        })
    }

    pub fn verify(&self, proof: &PartialTxProof) -> bool {
        let ptx_root = self.root();
        self.inputs.len() == proof.inputs.len()
            && self.outputs.len() == proof.outputs.len()
            && self
                .inputs
                .iter()
                .zip(&proof.inputs)
                .all(|(i, p)| i.verify(ptx_root, p))
            && self
                .outputs
                .iter()
                .zip(&proof.outputs)
                .all(|(o, p)| o.verify(p))
    }

    pub fn balance(&self) -> SubgroupPoint {
        let in_sum: SubgroupPoint = self.inputs.iter().map(|i| i.balance.0).sum();
        let out_sum: SubgroupPoint = self.outputs.iter().map(|o| o.balance.0).sum();

        out_sum - in_sum
    }
}

#[cfg(test)]
mod test {

    use crate::{note::NoteWitness, nullifier::NullifierSecret, test_util::seed_rng};

    use super::*;

    #[test]
    fn test_partial_tx_proof() {
        let mut rng = seed_rng(0);

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
            inputs: vec![nmo_10, eth_23],
            outputs: vec![crv_4840],
        };

        let ptx = PartialTx::from_witness(ptx_witness.clone());

        let ptx_proof = ptx.prove(ptx_witness, vec![vec![], vec![]]).unwrap();

        assert!(ptx.verify(&ptx_proof));
    }

    #[test]
    fn test_partial_tx_balance() {
        let mut rng = seed_rng(0);

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
            crate::balance::balance(4840, "CRV", crv_4840.note.balance.blinding)
                - (crate::balance::balance(10, "NMO", nmo_10.note.balance.blinding)
                    + crate::balance::balance(23, "ETH", eth_23.note.balance.blinding))
        );
    }
}
