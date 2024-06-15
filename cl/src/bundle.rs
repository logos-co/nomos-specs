use std::collections::BTreeSet;

use jubjub::{ExtendedPoint, Scalar};

use crate::{
    error::Error,
    note::NoteCommitment,
    partial_tx::{PartialTx, PartialTxProof, PartialTxWitness},
};

/// The transaction bundle is a collection of partial transactions.
/// The goal in bundling transactions is to produce a set of partial transactions
/// that balance each other.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Bundle {
    pub partials: Vec<PartialTx>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BundleWitness {
    pub partials: Vec<PartialTxWitness>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BundleProof {
    pub partials: Vec<PartialTxProof>,
}

impl Bundle {
    pub fn from_witness(w: BundleWitness) -> Self {
        Self {
            partials: Vec::from_iter(w.partials.into_iter().map(PartialTx::from_witness)),
        }
    }

    pub fn balance(&self) -> ExtendedPoint {
        self.partials.iter().map(|ptx| ptx.balance()).sum()
    }

    pub fn is_balanced(&self, balance_blinding_witness: Scalar) -> bool {
        self.balance() == crate::balance::balance(0, "", balance_blinding_witness)
    }

    pub fn prove(&self, w: BundleWitness) -> Result<BundleProof, Error> {
        if &Self::from_witness(w.clone()) != self {
            return Err(Error::ProofFailed);
        }
        if w.partials.len() == self.partials.len() {
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

        let ptx_proofs = self
            .partials
            .iter()
            .zip(w.partials)
            .map(|(ptx, p_w)| ptx.prove(p_w))
            .collect::<Result<Vec<PartialTxProof>, _>>()?;

        Ok(BundleProof {
            partials: ptx_proofs,
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

        let nmo_10_in = InputWitness::random(Note::new(10, "NMO"), &mut rng);
        let eth_23_in = InputWitness::random(Note::new(23, "ETH"), &mut rng);
        let crv_4840_out = OutputWitness::random(
            Note::new(4840, "CRV"),
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

        assert_eq!(
            bundle.balance(),
            crate::balance::balance(4840, "CRV", crv_4840_out.balance_blinding)
                - (crate::balance::balance(10, "NMO", nmo_10_in.balance_blinding)
                    + crate::balance::balance(23, "ETH", eth_23_in.balance_blinding))
        );

        let crv_4840_in = InputWitness::random(Note::new(4840, "CRV"), &mut rng);
        let nmo_10_out = OutputWitness::random(
            Note::new(10, "NMO"),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );
        let eth_23_out = OutputWitness::random(
            Note::new(23, "ETH"),
            NullifierSecret::random(&mut rng).commit(), // transferring to a random owner
            &mut rng,
        );

        bundle_witness.partials.push(PartialTxWitness {
            inputs: vec![crv_4840_in.clone()],
            outputs: vec![nmo_10_out.clone(), eth_23_out.clone()],
        });

        let bundle = Bundle::from_witness(bundle_witness);

        let blinding = -nmo_10_in.balance_blinding - eth_23_in.balance_blinding
            + crv_4840_out.balance_blinding
            - crv_4840_in.balance_blinding
            + nmo_10_out.balance_blinding
            + eth_23_out.balance_blinding;

        assert_eq!(bundle.balance(), crate::balance::balance(0, "", blinding));

        assert!(bundle.is_balanced(blinding));
    }
}
