use std::collections::BTreeSet;

use blake2::{Blake2s256, Digest};
use jubjub::SubgroupPoint;
use rand_core::RngCore;

use crate::error::Error;
use crate::input::{Input, InputProof, InputWitness};
use crate::output::{Output, OutputProof, OutputWitness};

/// The partial transaction commitment couples an input to a partial transaction.
/// Prevents partial tx unbundling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct PtxCommitment([u8; 32]);

impl PtxCommitment {
    pub fn random(mut rng: impl RngCore) -> Self {
        let mut sk = [0u8; 32];
        rng.fill_bytes(&mut sk);
        Self(sk)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialTx {
    pub inputs: Vec<Input>,
    pub outputs: Vec<Output>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialTxWitness {
    pub inputs: Vec<InputWitness>,
    pub outputs: Vec<OutputWitness>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialTxProof {
    pub inputs: Vec<InputProof>,
    pub outputs: Vec<OutputProof>,
}

impl PartialTx {
    pub fn from_witness(w: PartialTxWitness) -> Self {
        Self {
            inputs: Vec::from_iter(w.inputs.into_iter().map(Input::from_witness)),
            outputs: Vec::from_iter(w.outputs.into_iter().map(Output::from_witness)),
        }
    }

    pub fn commitment(&self) -> PtxCommitment {
        let mut hasher = Blake2s256::new();
        hasher.update(b"NOMOS_CL_PTX_COMMIT");
        hasher.update(b"INPUTS");
        for input in self.inputs.iter() {
            hasher.update(input.to_bytes());
        }
        hasher.update(b"OUTPUTS");
        for outputs in self.outputs.iter() {
            hasher.update(outputs.to_bytes());
        }

        let commit_bytes: [u8; 32] = hasher.finalize().into();
        PtxCommitment(commit_bytes)
    }

    pub fn prove(&self, w: PartialTxWitness) -> Result<PartialTxProof, Error> {
        if &Self::from_witness(w.clone()) != self {
            return Err(Error::ProofFailed);
        }
        let input_note_comms = BTreeSet::from_iter(self.inputs.iter().map(|i| i.note_comm));
        let output_note_comms = BTreeSet::from_iter(self.outputs.iter().map(|o| o.note_comm));

        if input_note_comms.len() != self.inputs.len()
            || output_note_comms.len() != self.outputs.len()
        {
            return Err(Error::ProofFailed);
        }

        let ptx_comm = self.commitment();

        let input_proofs: Vec<InputProof> = Result::from_iter(
            self.inputs
                .iter()
                .zip(&w.inputs)
                .map(|(i, i_w)| i.prove(i_w, ptx_comm)),
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
        let ptx_comm = self.commitment();
        self.inputs.len() == proof.inputs.len()
            && self.outputs.len() == proof.outputs.len()
            && self
                .inputs
                .iter()
                .zip(&proof.inputs)
                .all(|(i, p)| i.verify(ptx_comm, p))
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

    use crate::{note::Note, nullifier::NullifierSecret, test_util::seed_rng};

    use super::*;

    #[test]
    fn test_partial_tx_proof() {
        let mut rng = seed_rng(0);

        let nmo_10 = InputWitness::random(Note::random(10, "NMO", &mut rng), &mut rng);
        let eth_23 = InputWitness::random(Note::random(23, "ETH", &mut rng), &mut rng);
        let crv_4840 = OutputWitness::random(
            Note::random(4840, "CRV", &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        let ptx_witness = PartialTxWitness {
            inputs: vec![nmo_10, eth_23],
            outputs: vec![crv_4840],
        };

        let ptx = PartialTx::from_witness(ptx_witness.clone());

        let ptx_proof = ptx.prove(ptx_witness).unwrap();

        assert!(ptx.verify(&ptx_proof));
    }

    #[test]
    fn test_partial_tx_balance() {
        let mut rng = seed_rng(0);

        let nmo_10 = InputWitness::random(Note::random(10, "NMO", &mut rng), &mut rng);
        let eth_23 = InputWitness::random(Note::random(23, "ETH", &mut rng), &mut rng);
        let crv_4840 = OutputWitness::random(
            Note::random(4840, "CRV", &mut rng),
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
