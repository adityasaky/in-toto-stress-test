# in-toto-stress-test

This is a tool to generate large amounts of in-toto metadata. The idea is to
use this metadata to test the efficiency of in-toto's verification workflow in
various contexts.

## Installation and Usage

Clone this repository. The tool is written in Python, and makes use of
in-toto's reference implementation.

It's highly recommended you use this tool within a Python virtual environment.
The `requirements.txt` file can be used to install the necessary dependencies
using `pip`.

```bash
python make-supply-chain.py [--total INT --advanced INT]
```

A basic supply chain contains three steps: source code, test, and build. An
advanced supply chain contains an extra step that makes use of in-toto's
sublayout mechanism, pointing to a separate instance of a basic supply chain.
Therefore, the value for `advanced` has to be lesser than or equal to the value
for `total`.

The necessary keys are generated in the `keys` directory and the layout and
link metadata files in the `metadata` directory. Each top level supply chain's
links are stored in a subdirectory. Further, for advanced supply chains, the
link corresponding to the sublayout step is actually the layout of that
sublayout, with its link metadata in a further subdirectory.

Finally, verification can be invoked using the following bash script.

```bash
for i in {0..<total>}
do
  in-toto-verify -l metadata/supply-chain-$i.layout -k keys/supply-chain-$i-owner.pub --link-dir metadata/supply-chain-$i -vvv
done
```

The keys and metadata files generated can be cleaned up using the following
flag.

```bash
python make-supply-chain.py --clean
```