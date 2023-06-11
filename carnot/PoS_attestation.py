
import zlib
import random
import hashlib
from typing import List

from bitarray import bitarray

# This is the novel PoS attestation mechanism for Carnot. The goal of here is to avoid expensive O(n) signature
# aggregation and verification.

# A node receives bitarrays from its children, containing information on votes from its grand child committees.
def count_on_bitarray_fields(bitarrays, majority_threshold, threshold2):
    assert all(len(bitarray) == len(bitarrays[0]) for bitarray in bitarrays), "All bit arrays must have the same length"
    assert all(sum(bitarray) >= threshold2 for bitarray in
               bitarrays), "Each bit array must have at least threshold2 number of 'on' bits"

    num_bitarrays = len(bitarrays)
    array_size = len(bitarrays[0])  # Assuming all bit arrays have the same size

    result = [0] * array_size

    for i in range(array_size):
        count = sum(bitarray[i] for bitarray in bitarrays)
        if count >= majority_threshold:
            result[i] = 1  # or True

    return result




bitarrays = [
    [1, 0, 1, 0, 1],
    [0, 0, 1, 1, 1],
    [1, 0, 0, 1, 0]
]
threshold = 2
threshold2 = 1


result = count_on_bitarray_fields(bitarrays, threshold, threshold2)
print(result)  # Output: [1, 0, 1, 0, 1]


def getIndex(voteSet, sender):
    for index, vote in enumerate(voteSet):
        if sender == vote.voter:
            return index
    return -1  # Return -1 if the sender is not found in the idSet


def createCommitteeBitArray(voters, committee_size):
    committee_bit_array = [False] * committee_size
    assert committee_size >= len(voters)
    for vote in voters:
        sender = vote.voter
        print("voter is ", vote.voter)
        index = getIndex(voters, sender)
        if index >= 0 and index < committee_size:
            committee_bit_array[index] = True

    return committee_bit_array





def merge_bitarrays(bitarray1, bitarray2):
    merged_array = bitarray1 + bitarray2
    return merged_array




def compressBitArrays(*bit_arrays):
    # Flatten the bit arrays into a single list
    flat_array = [bit for bit_array in bit_arrays for bit in bit_array]

    # Convert the flat array to a bitarray object
    bitarray_object = bitarray(flat_array)
    print("flat bitarray is ", bitarray_object)
    # Compress the bitarray using zlib compression
    compressed_data = zlib.compress(bitarray_object.tobytes())
    return compressed_data


def decompressBitArray(compressed_data):
    # Decompress the compressed data using zlib decompression
    decompressed_data = zlib.decompress(compressed_data)

    # Convert the decompressed data back to a bitarray object
    bitarray_object = bitarray()
    bitarray_object.frombytes(decompressed_data)

    # Convert the bitarray object to a list
    decompressed_bitarray = bitarray_object.tolist()

    # Remove any additional padding zeros
    while decompressed_bitarray and decompressed_bitarray[-1] == 0:
        decompressed_bitarray.pop()

    return decompressed_bitarray




class Node:
    def __init__(self, identifier, stake):
        self.identifier = identifier
        self.stake = stake

def select_leader(nodes: List[Node], random_beacon: int) -> Node:
    total_stake = sum(node.stake for node in nodes)

    # calculate weighted hash output for each node
    weighted_hash_outputs = []
    for node in nodes:
        hash_input = str(random_beacon) + str(node.identifier)
        hash_output = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        weighted_hash_output = hash_output * node.stake
        weighted_hash_outputs.append(weighted_hash_output)

    # normalize weighted hash outputs to ensure that their sum is equal to total stake
    normalized_weighted_hash_outputs = [x / sum(weighted_hash_outputs) * total_stake for x in weighted_hash_outputs]

    # select leader based on normalized weighted hash outputs
    random_number = random.uniform(0, total_stake)
    cumulative_weighted_hash_output = 0
    for i, node in enumerate(nodes):
        cumulative_weighted_hash_output += normalized_weighted_hash_outputs[i]
        if cumulative_weighted_hash_output >= random_number:
            selected_leader = node
            break

    return selected_leader
