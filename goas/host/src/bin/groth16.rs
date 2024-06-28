/// Wrapping a STARK proof in groth16 in RISC0 should be as easy as specifying ProverOpts::groth16,
/// but unfortunately a permission issue seems to get in the way at least in the current machine we're
/// testing this on.
/// This workaround manually calls into docker after creating a directory with the required permissions.
/// In addition, splitting the process in different stages highlights better the different work that
/// needs to be done which could be split across different actors.

use std::path::PathBuf;
use clap::Parser;
use risc0_zkvm::{get_prover_server, ProverOpts, Receipt};

const WORK_DIR_ENV: &str = "RISC0_WORK_DIR";

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Path to the bincode-encoded STARK proof
    #[arg(short, long, default_value = "proof.stark")]
    input: PathBuf,

    /// Where to put the output artifacts
    #[arg(short, long, default_value = "output")]
    output_dir: PathBuf,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    // Initialize tracing. In order to view logs, run `RUST_LOG=info cargo run`
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::filter::EnvFilter::from_default_env())
        .init();

    let work_dir = tempfile::tempdir()?;
    // give permissions to the docker user to write to the work dir
    let mut perms = std::fs::metadata(&work_dir)?.permissions();
    // on unix this is for all users
    perms.set_readonly(false);
    std::fs::set_permissions(&work_dir, perms)?;

    let proof: Receipt = bincode::deserialize(&std::fs::read(&args.input)?)?;

    let server = get_prover_server(&ProverOpts::groth16())?;
    let converted = server.identity_p254(proof.inner.succinct()?)?;

    let work_dir_path = work_dir.path();
    std::env::set_var(WORK_DIR_ENV, work_dir_path);
    risc0_groth16::docker::stark_to_snark(&converted.get_seal_bytes())?;

    std::fs::create_dir_all(&args.output_dir)?;
    std::fs::copy(work_dir_path.join("proof.json"), args.output_dir.join("proof.json"))?;
    std::fs::copy(work_dir_path.join("public.json"), args.output_dir.join("public.json"))?;
    
    Ok(())
   }