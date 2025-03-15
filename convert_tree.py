"""
Convert existing tree JSON files to the format expected by the server.
"""

import json
import sys
from pathlib import Path


def convert_tree(input_file, output_name=None):
    """
    Convert an existing tree JSON file to the format expected by the server.

    Args:
        input_file: Path to the input JSON file
        output_name: Name for the output file (will be used as domain name)
    """
    # Load the input file
    with open(input_file, "r") as f:
        data = json.load(f)

    # Extract domain from filename if not provided
    if output_name is None:
        filename = Path(input_file).stem
        parts = filename.split("_")
        output_name = parts[0]
        if len(parts) > 1 and parts[-1] == "trees":
            output_name = "_".join(parts[:-1])

    # Create the output directory if it doesn't exist
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    # Define the output file path
    output_file = output_dir / f"{output_name}_trees.json"

    # Check if the input file has the expected keys
    if "conventional_tree" not in data and "enhanced_tree" not in data:
        # This is likely a file from the original tool, which needs conversion
        print(f"Converting {input_file} to the new format...")

        # Create a new structure
        new_data = {"conventional_tree": {}, "enhanced_tree": {}}

        # Try to extract trees from the input data
        if "trees" in data:
            if "conventional" in data["trees"]:
                new_data["conventional_tree"] = convert_tree_format(
                    data["trees"]["conventional"]
                )

            if "enhanced" in data["trees"]:
                new_data["enhanced_tree"] = convert_tree_format(
                    data["trees"]["enhanced"]
                )
        elif "conventional" in data:
            new_data["conventional_tree"] = convert_tree_format(data["conventional"])

            if "enhanced" in data:
                new_data["enhanced_tree"] = convert_tree_format(data["enhanced"])
        else:
            print("Warning: Could not identify tree structure in input file.")
    else:
        # Already in the expected format
        print(f"File {input_file} is already in the expected format.")
        new_data = data

    # Save the output file
    with open(output_file, "w") as f:
        json.dump(new_data, f, indent=2)

    print(f"Converted file saved to {output_file}")
    return output_file


def convert_tree_format(tree_data):
    """
    Convert a tree from the original format to the new format.

    Args:
        tree_data: Tree data in the original format

    Returns:
        Tree data in the new format
    """
    new_tree = {}

    # Check what format the input is in
    if isinstance(tree_data, dict) and "tree" in tree_data:
        # This is the format used in the JSON output
        nodes = tree_data["tree"]
        for node_id, node in nodes.items():
            new_tree[node_id] = {
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "data": node.get("data", {}),
                "parent": node.get("parent", ""),
                "children": node.get("children", []),
            }
    elif isinstance(tree_data, dict) and all(
        isinstance(k, str) for k in tree_data.keys()
    ):
        # This is already close to the expected format
        return tree_data
    else:
        print("Warning: Unrecognized tree format.")

    return new_tree


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python convert_tree.py <input_file> [output_name]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_name = None

    if len(sys.argv) >= 3:
        output_name = sys.argv[2]

    convert_tree(input_file, output_name)


if __name__ == "__main__":
    main()
