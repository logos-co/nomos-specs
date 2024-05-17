# Noir Circuits

this directory holds all the circuits written in Noir, used by the CL specification.

Each circuit is it's own nargo package under the `crates/` directory.

## Creating a new circuit

1. inside `crates/`, run `nargo new <circuit name>`
2. update `./Nargo.toml` to include the new circuit in the workspace

## Testing circuits

Under `./noir`, simple run.

```
nargo test
```
