import sys
import argparse
from securesystemslib import interface
from in_toto.models.metadata import Metablock
from in_toto.models.layout import Layout
from in_toto.runlib import in_toto_run
import os
import shutil


def create_basic_supply_chain(layout_name):
    # The basic layout needs four keys.
    # One key for the layout itself, one each for each step.

    owner_path = os.path.join("keys", layout_name + "-owner")
    source_path = os.path.join("keys", layout_name + "-source")
    test_path = os.path.join("keys", layout_name + "-test")
    build_path = os.path.join("keys", layout_name + "-build")

    # Create owner key
    interface._generate_and_write_rsa_keypair(filepath=owner_path)

    # Create functionary keys
    interface._generate_and_write_rsa_keypair(filepath=source_path)
    interface._generate_and_write_rsa_keypair(filepath=test_path)
    interface._generate_and_write_rsa_keypair(filepath=build_path)

    # Load private key for owner, public keys for functionaries
    owner_key = interface.import_rsa_privatekey_from_file(owner_path)
    source_key = interface.import_rsa_publickey_from_file(source_path + ".pub")
    test_key = interface.import_rsa_publickey_from_file(test_path + ".pub")
    build_key = interface.import_rsa_publickey_from_file(build_path + ".pub")

    # Create layout
    layout = Layout.read({
        "_type": "layout",
        "keys": {
            source_key["keyid"]: source_key,
            test_key["keyid"]: test_key,
            build_key["keyid"]: build_key,
        },
        "steps": [
            {
                "name": "source",
                "expected_materials": [],
                "expected_products": [],
                "pubkeys": [source_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
            {
                "name": "test",
                "expected_materials": [],
                "expected_products": [],
                "pubkeys": [test_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
            {
                "name": "build",
                "expected_materials": [],
                "expected_products": [],
                "pubkeys": [build_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
        ],
        "inspect": [],
    })

    metadata = Metablock(signed=layout)

    metadata.sign(owner_key)
    metadata.dump(os.path.join("metadata", layout_name + ".layout"))

    # Load functionary private keys
    source_key = interface.import_rsa_privatekey_from_file(source_path)
    test_key = interface.import_rsa_privatekey_from_file(test_path)
    build_key = interface.import_rsa_privatekey_from_file(build_path)

    os.mkdir(os.path.join("metadata", layout_name))

    # Generate link metadata
    source_link = in_toto_run("source", [], [], [], signing_key=source_key, metadata_directory=os.path.join("metadata", layout_name))
    test_link = in_toto_run("test", [], [], [], signing_key=test_key, metadata_directory=os.path.join("metadata", layout_name))
    build_link = in_toto_run("build", [], [], [], signing_key=build_key, metadata_directory=os.path.join("metadata", layout_name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--total", help="Total number of supply chains", type=int, default=4)
    parser.add_argument("-a", "--advanced", help="Number of advanced supply chains", type=int, default=1)
    parser.add_argument("-c", "--clean", help="Clean up created files", action="store_true")
    args = parser.parse_args()

    if args.clean:
        for f in os.listdir("keys"):
            if f != ".keep":
                os.remove(os.path.join("keys", f))
        for f in os.listdir("metadata"):
            if f != ".keep":
                p = os.path.join("metadata", f)
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(os.path.join("metadata", f))
        sys.exit(0)

    print("Welcome to the in-toto stress test!")
    print("This tool can be used to programmatically generate in-toto metadata using a specific template.")
    print("The basic supply chain has three steps: source code, test, and build.")
    print("A more advanced supply chain has the same steps, but also adds support for a sublayout, pointing to a separate instance of a basic supply chain.")

    assert args.advanced <= args.total

    for i in range(args.total):
        # TODO: A subset should create advanced supply chains
        create_basic_supply_chain("supply-chain-{}".format(i))


if __name__ == "__main__":
    main()