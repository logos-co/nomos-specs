use blake2::{Blake2s256, Digest};
use jubjub::ExtendedPoint;
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
    inputs: Vec<Input>,
    outputs: Vec<Output>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialTxWitness {
    inputs: Vec<InputWitness>,
    outputs: Vec<OutputWitness>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialTxProof {
    inputs: Vec<InputProof>,
    outputs: Vec<OutputProof>,
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

    pub fn balance(&self) -> ExtendedPoint {
        let in_sum: ExtendedPoint = self.inputs.iter().map(|i| i.balance).sum();
        let out_sum: ExtendedPoint = self.outputs.iter().map(|o| o.balance).sum();

        in_sum - out_sum
    }
}

#[cfg(test)]
mod test {

    use crate::{note::Note, nullifier::NullifierSecret, test_util::seed_rng};

    use super::*;

    #[test]
    fn test_partial_tx_proof() {
        let mut rng = seed_rng(0);

        let nmo_10 = InputWitness::random(Note::new(10, "NMO"), &mut rng);
        let eth_23 = InputWitness::random(Note::new(23, "ETH"), &mut rng);
        let crv_4840 = OutputWitness::random(
            Note::new(4840, "CRV"),
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
}
