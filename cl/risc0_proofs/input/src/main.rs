/// Input Proof
use cl::merkle;
use proof_statements::input::{InputPrivate, InputPublic};
use risc0_zkvm::guest::env;

fn main() {
    let secret: InputPrivate = env::read();

    let out_cm = secret.input.to_output_witness().commit_note();
    let cm_leaf = merkle::leaf(out_cm.as_bytes());
    let cm_root = merkle::path_root(cm_leaf, &secret.cm_path);

    env::commit(&InputPublic {
        input: secret.input.commit(),
        cm_root,
    });
}
