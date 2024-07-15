import sys

import pandas as pd


def calculate_hamming_distance(df1, df2):
    """
    Caculate the hamming distance between two DataFrames
    to quantify the difference between them.
    """
    if df1.shape != df2.shape:
        raise ValueError(
            "DataFrames must have the same shape to calculate Hamming distance."
        )

    # Compare element-wise and count differences
    differences = (df1 != df2).sum().sum()
    return differences / df1.size  # normalize the distance


def main():
    if len(sys.argv) != 3:
        print("Usage: python hamming.py <csv_path1> <csv_path2>")
        sys.exit(1)

    csv_path1 = sys.argv[1]
    csv_path2 = sys.argv[2]

    # Load the CSV files into DataFrames
    df1 = pd.read_csv(csv_path1)
    df2 = pd.read_csv(csv_path2)

    # Calculate the Hamming distance
    try:
        hamming_distance = calculate_hamming_distance(df1, df2)
        print(f"Hamming distance: {hamming_distance}")
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
