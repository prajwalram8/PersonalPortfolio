import os

def print_directory_structure(start_path, indent=0):
    # Print current directory
    print("  " * indent + f'[{start_path}]')

    # List all files and subdirectories in the current directory
    for item in os.listdir(start_path):
        item_path = os.path.join(start_path, item)

        # If it's a directory, recurse into it
        if os.path.isdir(item_path):
            print_directory_structure(item_path, indent + 1)
        else:
            print("  " * (indent + 1) + item)


if __name__ == "__main__":
    # Example usage
    print_directory_structure('.')
    