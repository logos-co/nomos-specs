from carnot_simulation_psuedocode import *

import time

def test_message_passing():
    # Test Case 1: Binary tree with 3 levels (L0, L1, L2)
    num_levels = 3
    root_committee = create_binary_tree_committees(num_levels)

    # Find the leaf committee at the lowest level
    leaf_committee = find_leaf_committee(root_committee)

    # Start message passing from the leaf committee at the lowest level and move towards the root at the highest level
    latency = 1  # Set the latency for message passing (you can adjust this as needed)
    start_time = time.time()
    result = simulate_message_passing(leaf_committee, latency)
    end_time = time.time()

    expected_result = num_levels - 1
    assert result == expected_result, f"Test Case 1 failed. Expected: {expected_result}, Got: {result}"
    print(expected_result)
    print(f"Test Case 1: Number of Levels Message Passed: {result}, Elapsed Time: {end_time - start_time:.4f} seconds")

    # Test Case 2: Binary tree with 5 levels (L0, L1, L2, L3, L4)
    num_levels = 5
    root_committee = create_binary_tree_committees(num_levels)

    # Find the leaf committee at the lowest level
    leaf_committee = find_leaf_committee(root_committee)

    # Start message passing from the leaf committee at the lowest level and move towards the root at the highest level
    latency = 0.5  # Set the latency for message passing (you can adjust this as needed)
    start_time = time.time()
    result = simulate_message_passing(leaf_committee, latency)
    end_time = time.time()

    expected_result = num_levels - 1
    assert result == expected_result, f"Test Case 2 failed. Expected: {expected_result}, Got: {result}"

    print(f"Test Case 2: Number of Levels Message Passed: {result}, Elapsed Time: {end_time - start_time:.4f} seconds")

    # Test Case 3: Binary tree with 1 level (Only the root committee)
    num_levels = 1
    root_committee = create_binary_tree_committees(num_levels)

    # Find the leaf committee at the lowest level (which is also the root)
    leaf_committee = find_leaf_committee(root_committee)

    # Start message passing from the leaf committee (which is also the root)
    latency = 0.1  # Set the latency for message passing (you can adjust this as needed)
    start_time = time.time()
    result = simulate_message_passing(leaf_committee, latency)
    end_time = time.time()

    expected_result = num_levels - 1
    assert result == expected_result, f"Test Case 3 failed. Expected: {expected_result}, Got: {result}"

    print(f"Test Case 3: Number of Levels Message Passed: {result}, Elapsed Time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    test_message_passing()
