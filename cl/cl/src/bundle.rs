use serde::{Deserialize, Serialize};

use curve25519_dalek::{constants::RISTRETTO_BASEPOINT_POINT, ristretto::RistrettoPoint, Scalar};

use crate::partial_tx::PartialTx;

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

impl Bundle {
    pub fn balance(&self) -> RistrettoPoint {
        self.partials.iter().map(|ptx| ptx.balance()).sum()
    }

    pub fn is_balanced(&self, balance_blinding_witness: Scalar) -> bool {
        self.balance()
            == crate::balance::balance(0, RISTRETTO_BASEPOINT_POINT, balance_blinding_witness)
    }
}

#[cfg(test)]
mod test {
    use crate::{
        crypto::hash_to_curve, input::InputWitness, note::NoteWitness, nullifier::NullifierSecret,
        output::OutputWitness, partial_tx::PartialTxWitness,
    };

    use super::*;

    #[test]
    fn test_bundle_balance() {
        let mut rng = rand::thread_rng();

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
            crate::balance::balance(
                4840,
                hash_to_curve(b"CRV"),
                crv_4840_out.note.balance.blinding
            ) - (crate::balance::balance(
                10,
                hash_to_curve(b"NMO"),
                nmo_10_in.note.balance.blinding
            ) + crate::balance::balance(
                23,
                hash_to_curve(b"ETH"),
                eth_23_in.note.balance.blinding
            ))
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
            crate::balance::balance(
                0,
                curve25519_dalek::constants::RISTRETTO_BASEPOINT_POINT,
                witness.balance_blinding
            )
        );

        assert!(bundle.is_balanced(witness.balance_blinding));
    }
}
