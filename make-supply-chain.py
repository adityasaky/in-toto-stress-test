import sys
import argparse
from securesystemslib import interface
from in_toto.models.metadata import Metablock
from in_toto.models.layout import Layout
from in_toto.runlib import in_toto_run
import os
import shutil


def create_basic_supply_chain(layout_name, parent_layout=""):
    # FIXME: parent_layout can imply a boolean argument that says this is a parent layout rather than a sublayout
    owner_path = os.path.join("keys", layout_name + "-owner")
    source_path = os.path.join("keys", layout_name + "-source")
    test_path = os.path.join("keys", layout_name + "-test")
    build_path = os.path.join("keys", layout_name + "-build")

    artifact_path = os.path.join("artifacts", layout_name + ".src")

    # Create owner key
    interface._generate_and_write_rsa_keypair(filepath=owner_path)

    # Create functionary keys
    interface._generate_and_write_rsa_keypair(filepath=source_path)
    interface._generate_and_write_rsa_keypair(filepath=test_path)
    # FIXME: don't generate build keys if sublayout
    interface._generate_and_write_rsa_keypair(filepath=build_path)

    # Load private key for owner, public keys for functionaries
    owner_key = interface.import_rsa_privatekey_from_file(owner_path)
    source_key = interface.import_rsa_publickey_from_file(source_path + ".pub")
    test_key = interface.import_rsa_publickey_from_file(test_path + ".pub")
    build_key = interface.import_rsa_publickey_from_file(build_path + ".pub")

    # Create layout
    if parent_layout:
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
                    "expected_materials": [["DISALLOW", "*"]],
                    "expected_products": [["CREATE", artifact_path], ["DISALLOW", "*"]],
                    "pubkeys": [source_key["keyid"]],
                    "expected_command": ["echo", layout_name],
                    "threshold": 1,
                },
                {
                    "name": "test",
                    "expected_materials": [["MATCH", artifact_path, "WITH", "PRODUCTS", "FROM", "source"], ["DISALLOW", "*"]],
                    "expected_products": [["ALLOW", artifact_path], ["DISALLOW", "*"]],
                    "pubkeys": [test_key["keyid"]],
                    "expected_command": [],
                    "threshold": 1,
                },
            ],
            "inspect": [],
        })
    else:
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
                    "expected_materials": [["DISALLOW", "*"]],
                    "expected_products": [["CREATE", artifact_path], ["DISALLOW", "*"]],
                    "pubkeys": [source_key["keyid"]],
                    "expected_command": [],
                    "threshold": 1,
                },
                {
                    "name": "test",
                    "expected_materials": [["MATCH", artifact_path, "WITH", "PRODUCTS", "FROM", "source"], ["DISALLOW", "*"]],
                    "expected_products": [["ALLOW", artifact_path], ["DISALLOW", "*"]],
                    "pubkeys": [test_key["keyid"]],
                    "expected_command": [],
                    "threshold": 1,
                },
                {
                    "name": "build",
                    "expected_materials": [["MATCH", artifact_path, "WITH", "PRODUCTS", "FROM", "test"], ["DISALLOW", "*"]],
                    "expected_products": [["CREATE", artifact_path + ".tar.gz"], ["DISALLOW", "*"]],
                    "pubkeys": [build_key["keyid"]],
                    "expected_command": [],
                    "threshold": 1,
                },
            ],
            "inspect": [],
        })

    metadata = Metablock(signed=layout, compact_json=True)

    metadata.sign(owner_key)

    if parent_layout:
        metadata.dump(os.path.join("metadata", parent_layout, "tier-2-supply-chain.{keyid:.8}.link".format(keyid=owner_key["keyid"])))  # FIXME: Is it okay to hard code this?
    else:
        metadata.dump(os.path.join("metadata", layout_name + ".layout"))

    # Load functionary private keys
    source_key = interface.import_rsa_privatekey_from_file(source_path)
    test_key = interface.import_rsa_privatekey_from_file(test_path)
    build_key = interface.import_rsa_privatekey_from_file(build_path)

    # Generate link metadata
    if parent_layout:
        sublayout_link_dir = os.path.join("metadata", parent_layout, "tier-2-supply-chain.{keyid:.8}".format(keyid=owner_key["keyid"]))
        os.mkdir(sublayout_link_dir)

        with open(artifact_path, "w+") as f:
            f.write(layout_name + "\n")
        source_link = in_toto_run("source", [], [artifact_path], ["echo", layout_name], signing_key=source_key, metadata_directory=sublayout_link_dir, compact_json=True)
        test_link = in_toto_run("test", [artifact_path], [artifact_path], [], signing_key=test_key, metadata_directory=sublayout_link_dir, compact_json=True)
        # build_link = in_toto_run("build", [artifact_path], [artifact_path + ".tar.gz"], ["tar", "-czf", artifact_path + ".tar.gz", artifact_path], signing_key=build_key, metadata_directory=sublayout_link_dir)
    else:
        os.mkdir(os.path.join("metadata", layout_name))

        with open(artifact_path, "w+") as f:
            f.write(layout_name + "\n")
        source_link = in_toto_run("source", [], [artifact_path], ["echo", layout_name], signing_key=source_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)
        test_link = in_toto_run("test", [artifact_path], [artifact_path], [], signing_key=test_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)
        build_link = in_toto_run("build", [artifact_path], [artifact_path + ".tar.gz"], ["tar", "-czf", artifact_path + ".tar.gz", artifact_path], signing_key=build_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)


def create_advanced_supply_chain(layout_name):
    os.mkdir(os.path.join("metadata", layout_name))
    sublayout_name = layout_name + "-sublayout"
    create_basic_supply_chain(sublayout_name, parent_layout=layout_name)

    owner_path = os.path.join("keys", layout_name + "-owner")
    source_path = os.path.join("keys", layout_name + "-source")
    sublayout_path = os.path.join("keys", sublayout_name + "-owner")
    test_path = os.path.join("keys", layout_name + "-test")
    build_path = os.path.join("keys", layout_name + "-build")

    artifact_path = os.path.join("artifacts", layout_name + ".src")
    sublayout_artifact_path = os.path.join("artifacts", sublayout_name + ".src")

    # Create owner key
    interface._generate_and_write_rsa_keypair(filepath=owner_path)

    # Create functionary keys
    interface._generate_and_write_rsa_keypair(filepath=source_path)
    interface._generate_and_write_rsa_keypair(filepath=test_path)
    interface._generate_and_write_rsa_keypair(filepath=build_path)

    # Load private key for owner, public keys for functionaries
    owner_key = interface.import_rsa_privatekey_from_file(owner_path)
    source_key = interface.import_rsa_publickey_from_file(source_path + ".pub")
    sublayout_key = interface.import_rsa_publickey_from_file(sublayout_path + ".pub")
    test_key = interface.import_rsa_publickey_from_file(test_path + ".pub")
    build_key = interface.import_rsa_publickey_from_file(build_path + ".pub")

    # Create layout
    layout = Layout.read({
        "_type": "layout",
        "keys": {
            source_key["keyid"]: source_key,
            sublayout_key["keyid"]: sublayout_key,
            test_key["keyid"]: test_key,
            build_key["keyid"]: build_key,
        },
        "steps": [
            {
                "name": "source",
                "expected_materials": [["DISALLOW", "*"]],
                "expected_products": [["CREATE", artifact_path], ["DISALLOW", "*"]],
                "pubkeys": [source_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
            {
                "name": "tier-2-supply-chain",
                "expected_materials": [["DISALLOW", "*"]],
                "expected_products": [["CREATE", sublayout_artifact_path], ["DISALLOW", "*"]],
                "pubkeys": [sublayout_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
            {
                "name": "test",
                "expected_materials": [["MATCH", artifact_path, "WITH", "PRODUCTS", "FROM", "source"], ["MATCH", sublayout_artifact_path, "WITH", "PRODUCTS", "FROM", "tier-2-supply-chain"], ["DISALLOW", "*"]],
                "expected_products": [["ALLOW", artifact_path], ["ALLOW", sublayout_artifact_path], ["DISALLOW", "*"]],
                "pubkeys": [test_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
            {
                "name": "build",
                "expected_materials": [["MATCH", "*", "WITH", "PRODUCTS", "FROM", "test"], ["DISALLOW", "*"]],
                "expected_products": [["CREATE", artifact_path + ".tar.gz"], ["DISALLOW", "*"]],
                "pubkeys": [build_key["keyid"]],
                "expected_command": [],
                "threshold": 1,
            },
        ],
        "inspect": [],
    })

    metadata = Metablock(signed=layout, compact_json=True)

    metadata.sign(owner_key)
    metadata.dump(os.path.join("metadata", layout_name + ".layout"))

    # Load functionary private keys
    source_key = interface.import_rsa_privatekey_from_file(source_path)
    test_key = interface.import_rsa_privatekey_from_file(test_path)
    build_key = interface.import_rsa_privatekey_from_file(build_path)

    # Generate link metadata
    with open(artifact_path, "w+") as f:
        f.write(layout_name + "\n")
    source_link = in_toto_run("source", [], [artifact_path], ["echo", layout_name], signing_key=source_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)
    test_link = in_toto_run("test", [artifact_path, sublayout_artifact_path], [artifact_path, sublayout_artifact_path], [], signing_key=test_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)
    build_link = in_toto_run("build", [artifact_path, sublayout_artifact_path], [artifact_path + ".tar.gz"], ["tar", "-czf", artifact_path + ".tar.gz", artifact_path, sublayout_artifact_path], signing_key=build_key, metadata_directory=os.path.join("metadata", layout_name), compact_json=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--total", help="Total number of supply chains", type=int, default=4)
    parser.add_argument("-a", "--advanced", help="Number of advanced supply chains", type=int, default=1)
    parser.add_argument("-c", "--clean", help="Clean up created files", action="store_true")
    args = parser.parse_args()

    if args.clean:
        for f in os.listdir("artifacts"):
            if f != ".keep":
                os.remove(os.path.join("artifacts", f))
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
        if i < args.advanced:
            create_advanced_supply_chain("supply-chain-{}".format(i))
        else:
            create_basic_supply_chain("supply-chain-{}".format(i))


if __name__ == "__main__":
    main()