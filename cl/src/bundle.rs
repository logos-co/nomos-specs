use std::collections::BTreeSet;

use jubjub::{Scalar, SubgroupPoint};
use serde::{Deserialize, Serialize};

use crate::{
    error::Error,
    note::NoteCommitment,
    partial_tx::{PartialTx, PartialTxProof},
};

/// The transaction bundle is a collection of partial transactions.
/// The goal in bundling transactions is to produce a set of partial transactions
/// that balance each other.

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bundle {
    pub partials: Vec<PartialTx>,
}

#[derive(Debug, Clone)]
pub struct BundleWitness {
    pub balance_blinding: Scalar,
}

#[derive(Debug)]
pub struct BundleProof {
    pub partials: Vec<PartialTxProof>,
    pub balance_blinding: Scalar,
}

impl Bundle {
    pub fn balance(&self) -> SubgroupPoint {
        self.partials.iter().map(|ptx| ptx.balance()).sum()
    }

    pub fn is_balanced(&self, balance_blinding_witness: Scalar) -> bool {
        self.balance() == crate::balance::balance(0, "", balance_blinding_witness)
    }

    pub fn prove(
        &self,
        w: BundleWitness,
        ptx_proofs: Vec<PartialTxProof>,
    ) -> Result<BundleProof, Error> {
        if ptx_proofs.len() == self.partials.len() {
            return Err(Error::ProofFailed);
        }
        let input_notes: Vec<NoteCommitment> = self
            .partials
            .iter()
            .flat_map(|ptx| ptx.inputs.iter().map(|i| i.note_comm))
            .collect();
        if input_notes.len() != BTreeSet::from_iter(input_notes.iter()).len() {
            return Err(Error::ProofFailed);
        }

        let output_notes: Vec<NoteCommitment> = self
            .partials
            .iter()
            .flat_map(|ptx| ptx.outputs.iter().map(|o| o.note_comm))
            .collect();
        if output_notes.len() != BTreeSet::from_iter(output_notes.iter()).len() {
            return Err(Error::ProofFailed);
        }

        if self.balance() != crate::balance::balance(0, "", w.balance_blinding) {
            return Err(Error::ProofFailed);
        }

        Ok(BundleProof {
            partials: ptx_proofs,
            balance_blinding: w.balance_blinding,
        })
    }

    pub fn verify(&self, proof: BundleProof) -> bool {
        proof.partials.len() == self.partials.len()
            && self
                .partials
                .iter()
                .zip(&proof.partials)
                .all(|(p, p_proof)| p.verify(p_proof))
    }
}

#[cfg(test)]
mod test {
    use crate::{
        input::InputWitness, note::Note, nullifier::NullifierSecret, output::OutputWitness,
        test_util::seed_rng,
    };

    use super::*;

    #[test]
    fn test_bundle_balance() {
        let mut rng = seed_rng(0);

        let nmo_10_in = InputWitness::random(Note::random(10, "NMO", &mut rng), &mut rng);
        let eth_23_in = InputWitness::random(Note::random(23, "ETH", &mut rng), &mut rng);
        let crv_4840_out = OutputWitness::random(
            Note::random(4840, "CRV", &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        let mut bundle_witness = BundleWitness {
            partials: vec![PartialTxWitness {
                inputs: vec![nmo_10_in.clone(), eth_23_in.clone()],
                outputs: vec![crv_4840_out.clone()],
            }],
        };

        let bundle = Bundle::from_witness(bundle_witness.clone());

        assert!(!bundle.is_balanced(
            -nmo_10_in.note.balance.blinding - eth_23_in.note.balance.blinding
                + crv_4840_out.note.balance.blinding
        ));
        assert_eq!(
            bundle.balance(),
            crate::balance::balance(4840, "CRV", crv_4840_out.note.balance.blinding)
                - (crate::balance::balance(10, "NMO", nmo_10_in.note.balance.blinding)
                    + crate::balance::balance(23, "ETH", eth_23_in.note.balance.blinding))
        );

        let crv_4840_in = InputWitness::random(Note::random(4840, "CRV", &mut rng), &mut rng);
        let nmo_10_out = OutputWitness::random(
            Note::random(10, "NMO", &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );
        let eth_23_out = OutputWitness::random(
            Note::random(23, "ETH", &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        bundle_witness.partials.push(PartialTxWitness {
            inputs: vec![crv_4840_in.clone()],
            outputs: vec![nmo_10_out.clone(), eth_23_out.clone()],
        });

        let bundle = Bundle::from_witness(bundle_witness);

        let blinding = -nmo_10_in.note.balance.blinding - eth_23_in.note.balance.blinding
            + crv_4840_out.note.balance.blinding
            - crv_4840_in.note.balance.blinding
            + nmo_10_out.note.balance.blinding
            + eth_23_out.note.balance.blinding;

        assert_eq!(bundle.balance(), crate::balance::balance(0, "", blinding));

        assert!(bundle.is_balanced(blinding));
    }
}
