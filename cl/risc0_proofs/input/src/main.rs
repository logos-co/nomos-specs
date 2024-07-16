/// Input Proof
use cl::merkle;
use cl::nullifier::Nullifier;
use proof_statements::input::{InputPrivate, InputPublic};
use risc0_zkvm::guest::env;

fn main() {
    let secret: InputPrivate = env::read();
    assert_eq!(secret.output.nf_pk, secret.nf_sk.commit());

    let cm_out = secret.output.commit_note();
    let cm_leaf = merkle::leaf(cm_out.as_bytes());
    let cm_root = merkle::path_root(cm_leaf, &secret.cm_path);

    let nf = Nullifier::new(secret.nf_sk, secret.output.nonce);

    let death_cm = secret.output.note.death_commitment();

    env::commit(&InputPublic {
        cm_root,
        nf,
        death_cm,
    });
}
