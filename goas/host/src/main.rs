// These constants represent the RISC-V ELF and the image ID generated by risc0-build.
// The ELF is used for proving and the ID is used for verification.
use blake2::{Blake2s256, Digest};
use methods::{METHOD_ELF, METHOD_ID};
use risc0_zkvm::{default_prover, ExecutorEnv};
use common::*;
use cl::note::NoteWitness;
use cl::input::InputWitness;
use cl::output::OutputWitness;
use cl::nullifier::NullifierSecret;
use cl::partial_tx::{PartialTx, PartialTxWitness};
use cl::merkle;

fn main() {
    // Initialize tracing. In order to view logs, run `RUST_LOG=info cargo run`
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::filter::EnvFilter::from_default_env())
        .init();

    let mut rng = rand::thread_rng();

    let state: State = [(0, 1000)].into_iter().collect();
    let journal = vec![];
    let zone_input = Input::Transfer {
        from: 0,
        to: 1,
        amount: 10,
    };

    let in_state_cm = calculate_state_hash(&state);
    let in_journal_cm = calculate_journal_hash(&journal);
    let in_state_root = merkle::node(in_state_cm, in_journal_cm);
    let in_note = NoteWitness::new(1, "ZONE", in_state_root, &mut rng);

    let mut out_journal = journal.clone();
    out_journal.push(zone_input);

    let out_state_cm = calculate_state_hash(&stf(state.clone(), zone_input));
    let out_journal_cm = calculate_journal_hash(&out_journal);
    let out_state_root = merkle::node(out_state_cm, out_journal_cm);
    let out_note = NoteWitness::new(1, "ZONE", out_state_root, &mut rng);

    let input = InputWitness::random(in_note, &mut rng);
    let output = OutputWitness::random(out_note, NullifierSecret::random(&mut rng).commit(), &mut rng);
    let ptx = PartialTx::from_witness(PartialTxWitness {
        inputs: vec![input.clone()],
        outputs: vec![output.clone()],
    });

    let ptx_root = ptx.root().0;
    let in_ptx_path = ptx.input_merkle_path(0);
    let out_ptx_path = ptx.output_merkle_path(0);

    let env = ExecutorEnv::builder()
        .write(&ptx_root)
        .unwrap()
        .write(&ptx.input_root())
        .unwrap()
        .write(&ptx.output_root())
        .unwrap()
        .write(&in_ptx_path)
        .unwrap()
        .write(&out_ptx_path)
        .unwrap()
        .write(&input)
        .unwrap()
        .write(&output)
        .unwrap()
        .write(&zone_input)
        .unwrap()
        .write(&state)
        .unwrap()
        .write(&journal)
        .unwrap()
        .build()
        .unwrap();

    // Obtain the default prover.
    let prover = default_prover();

    // Proof information by proving the specified ELF binary.
    // This struct contains the receipt along with statistics about execution of the guest
    let opts = risc0_zkvm::ProverOpts::succinct();
    let prove_info = prover.prove_with_opts(env, METHOD_ELF, &opts).unwrap();

    // extract the receipt.
    let receipt = prove_info.receipt;

    // TODO: Implement code for retrieving receipt journal here.

    std::fs::write("proof.stark", bincode::serialize(&receipt).unwrap()).unwrap();
    // The receipt was verified at the end of proving, but the below code is an
    // example of how someone else could verify this receipt.
    receipt.verify(METHOD_ID).unwrap();
}

fn calculate_state_hash(state: &State) -> [u8; 32] {
    let bytes = bincode::serialize(state).unwrap();
    Blake2s256::digest(&bytes).into()
}

fn calculate_journal_hash(journal: &Journal) -> [u8; 32] {
    let bytes = bincode::serialize(journal).unwrap();
    Blake2s256::digest(&bytes).into()
}
