use proof_statements::nullifier::{NullifierPrivate, NullifierPublic};

use crate::error::Result;

const MAX_NOTE_COMMS: usize = 2usize.pow(8);

#[derive(Debug, Clone)]
pub struct InputNullifierProof {
    receipt: risc0_zkvm::Receipt,
}

impl InputNullifierProof {
    pub fn public(&self) -> Result<NullifierPublic> {
        Ok(self.receipt.journal.decode()?)
    }

    pub fn verify(&self, expected_public_inputs: NullifierPublic) -> bool {
        let Ok(public_inputs) = self.public() else {
            return false;
        };

        public_inputs == expected_public_inputs
            && self
                .receipt
                .verify(nomos_cl_risc0_proofs::NULLIFIER_ID)
                .is_ok()
    }
}

pub fn prove_input_nullifier(
    input: &cl::InputWitness,
    note_commitments: &[cl::NoteCommitment],
) -> InputNullifierProof {
    let output = input.to_output_witness();
    let cm_leaves = note_commitment_leaves(note_commitments);
    let output_cm = output.commit_note();
    let cm_idx = note_commitments
        .iter()
        .position(|c| c == &output_cm)
        .unwrap();
    let cm_path = cl::merkle::path(cm_leaves, cm_idx);

    let secrets = NullifierPrivate {
        nf_sk: input.nf_sk,
        output,
        cm_path,
    };

    let env = risc0_zkvm::ExecutorEnv::builder()
        .write(&secrets)
        .unwrap()
        .build()
        .unwrap();

    // Obtain the default prover.
    let prover = risc0_zkvm::default_prover();

    use std::time::Instant;
    let start_t = Instant::now();

    // Proof information by proving the specified ELF binary.
    // This struct contains the receipt along with statistics about execution of the guest
    let opts = risc0_zkvm::ProverOpts::succinct();
    let prove_info = prover
        .prove_with_opts(env, nomos_cl_risc0_proofs::NULLIFIER_ELF, &opts)
        .unwrap();

    println!(
        "STARK prover time: {:.2?}, total_cycles: {}",
        start_t.elapsed(),
        prove_info.stats.total_cycles
    );
    // extract the receipt.
    let receipt = prove_info.receipt;
    InputNullifierProof { receipt }
}

fn note_commitment_leaves(note_commitments: &[cl::NoteCommitment]) -> [[u8; 32]; MAX_NOTE_COMMS] {
    let note_comm_bytes = Vec::from_iter(note_commitments.iter().map(|c| c.as_bytes().to_vec()));
    let cm_leaves = cl::merkle::padded_leaves::<MAX_NOTE_COMMS>(&note_comm_bytes);
    cm_leaves
}

#[cfg(test)]
mod test {
    use proof_statements::nullifier::NullifierPublic;
    use rand::thread_rng;

    use super::{note_commitment_leaves, prove_input_nullifier};

    #[test]
    fn test_input_nullifier_prover() {
        let mut rng = thread_rng();
        let input = cl::InputWitness {
            note: cl::NoteWitness {
                balance: cl::BalanceWitness::random(32, "NMO", &mut rng),
                death_constraint: vec![],
                state: [0u8; 32],
            },
            nf_sk: cl::NullifierSecret::random(&mut rng),
            nonce: cl::NullifierNonce::random(&mut rng),
        };

        let notes = vec![input.to_output_witness().commit_note()];

        let proof = prove_input_nullifier(&input, &notes);

        let expected_public_inputs = NullifierPublic {
            cm_root: cl::merkle::root(note_commitment_leaves(&notes)),
            nf: input.commit().nullifier,
        };

        assert!(proof.verify(expected_public_inputs));

        let wrong_public_inputs = NullifierPublic {
            cm_root: cl::merkle::root(note_commitment_leaves(&notes)),
            nf: cl::Nullifier::new(
                cl::NullifierSecret::random(&mut rng),
                cl::NullifierNonce::random(&mut rng),
            ),
        };

        assert!(!proof.verify(wrong_public_inputs));
    }

    #[test]
    fn test_input_proof() {
        let mut rng = rand::thread_rng();

        let ptx_root = PtxRoot::default();

        let note = NoteWitness::new(10, "NMO", [0u8; 32], &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let input_witness = InputWitness { note, nf_sk, nonce };

        let input = input_witness.commit();
        let proof = input.prove(&input_witness, ptx_root, vec![]).unwrap();

        assert!(input.verify(ptx_root, &proof));

        let wrong_witnesses = [
            InputWitness {
                note: NoteWitness::new(11, "NMO", [0u8; 32], &mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                note: NoteWitness::new(10, "ETH", [0u8; 32], &mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                nf_sk: NullifierSecret::random(&mut rng),
                ..input_witness.clone()
            },
            InputWitness {
                nonce: NullifierNonce::random(&mut rng),
                ..input_witness.clone()
            },
        ];

        for wrong_witness in wrong_witnesses {
            assert!(input.prove(&wrong_witness, ptx_root, vec![]).is_err());

            let wrong_input = wrong_witness.commit();
            let wrong_proof = wrong_input.prove(&wrong_witness, ptx_root, vec![]).unwrap();
            assert!(!input.verify(ptx_root, &wrong_proof));
        }
    }

    #[test]
    fn test_input_ptx_coupling() {
        let mut rng = seed_rng(0);

        let note = NoteWitness::new(10, "NMO", [0u8; 32], &mut rng);
        let nf_sk = NullifierSecret::random(&mut rng);
        let nonce = NullifierNonce::random(&mut rng);

        let witness = InputWitness { note, nf_sk, nonce };

        let input = witness.commit();

        let ptx_root = PtxRoot::random(&mut rng);
        let proof = input.prove(&witness, ptx_root, vec![]).unwrap();

        assert!(input.verify(ptx_root, &proof));

        // The same input proof can not be used in another partial transaction.
        let another_ptx_root = PtxRoot::random(&mut rng);
        assert!(!input.verify(another_ptx_root, &proof));
    }
}
