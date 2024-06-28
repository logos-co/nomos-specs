use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use k256::{Scalar, ProjectivePoint};

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
    pub fn balance(&self) -> ProjectivePoint {
        self.partials.iter().map(|ptx| ptx.balance()).sum()
    }

    pub fn is_balanced(&self, balance_blinding_witness: Scalar) -> bool {
        self.balance() == crate::balance::balance(0, ProjectivePoint::GENERATOR, balance_blinding_witness)
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

        if self.balance() != crate::balance::balance(0, ProjectivePoint::GENERATOR, w.balance_blinding) {
            return Err(Error::ProofFailed);
        }

        Ok(BundleProof {
            partials: ptx_proofs,
            balance_blinding: w.balance_blinding,
        })
    }

    pub fn verify(&self, proof: BundleProof) -> bool {
        proof.partials.len() == self.partials.len()
            && self.is_balanced(proof.balance_blinding)
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
        input::InputWitness, note::NoteWitness, nullifier::NullifierSecret, output::OutputWitness,
        partial_tx::PartialTxWitness, test_util::seed_rng,
        crypto::hash_to_curve,
    };

    use super::*;

    #[test]
    fn test_bundle_balance() {
        let mut rng = seed_rng(0);

        let nmo_10_in =
            InputWitness::random(NoteWitness::new(10, "NMO", [0u8; 32], &mut rng), &mut rng);
        let eth_23_in =
            InputWitness::random(NoteWitness::new(23, "ETH", [0u8; 32], &mut rng), &mut rng);
        let crv_4840_out = OutputWitness::random(
            NoteWitness::new(4840, "CRV", [0u8; 32], &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        let ptx_unbalanced = PartialTxWitness {
            inputs: vec![nmo_10_in.clone(), eth_23_in.clone()],
            outputs: vec![crv_4840_out.clone()],
        };

        let bundle_witness = BundleWitness {
            balance_blinding: crv_4840_out.note.balance.blinding
                - nmo_10_in.note.balance.blinding
                - eth_23_in.note.balance.blinding,
        };

        let mut bundle = Bundle {
            partials: vec![PartialTx::from_witness(ptx_unbalanced)],
        };

        assert!(!bundle.is_balanced(bundle_witness.balance_blinding));
        assert_eq!(
            bundle.balance(),
            crate::balance::balance(4840, hash_to_curve(b"CRV"), crv_4840_out.note.balance.blinding)
                - (crate::balance::balance(10, hash_to_curve(b"NMO"), nmo_10_in.note.balance.blinding)
                    + crate::balance::balance(23, hash_to_curve(b"ETH"), eth_23_in.note.balance.blinding))
        );

        let crv_4840_in =
            InputWitness::random(NoteWitness::new(4840, "CRV", [0u8; 32], &mut rng), &mut rng);
        let nmo_10_out = OutputWitness::random(
            NoteWitness::new(10, "NMO", [0u8; 32], &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );
        let eth_23_out = OutputWitness::random(
            NoteWitness::new(23, "ETH", [0u8; 32], &mut rng),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        bundle
            .partials
            .push(PartialTx::from_witness(PartialTxWitness {
                inputs: vec![crv_4840_in.clone()],
                outputs: vec![nmo_10_out.clone(), eth_23_out.clone()],
            }));

        let witness = BundleWitness {
            balance_blinding: -nmo_10_in.note.balance.blinding - eth_23_in.note.balance.blinding
                + crv_4840_out.note.balance.blinding
                - crv_4840_in.note.balance.blinding
                + nmo_10_out.note.balance.blinding
                + eth_23_out.note.balance.blinding,
        };

        assert_eq!(
            bundle.balance(),
            crate::balance::balance(0, ProjectivePoint::GENERATOR, witness.balance_blinding)
        );

        assert!(bundle.is_balanced(witness.balance_blinding));
    }
}
