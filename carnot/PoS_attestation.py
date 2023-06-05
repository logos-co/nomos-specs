
import random
import zlib

from bitarray import bitarray

# This is the novel PoS attestation mechanism for Carnot. The goal of here is to avoid expensive O(n) signature
# aggregation and verification.

# A node receives bitarrays from its children, containing information on votes from its grand child committees.
def count_on_bitarray_fields(bitarrays, threshold, threshold2):
    assert all(len(bitarray) == len(bitarrays[0]) for bitarray in bitarrays), "All bit arrays must have the same length"
    assert all(sum(bitarray) >= threshold2 for bitarray in
               bitarrays), "Each bit array must have at least threshold2 number of 'on' bits"

    num_bitarrays = len(bitarrays)
    array_size = len(bitarrays[0])  # Assuming all bit arrays have the same size

    result = [0] * array_size

    for i in range(array_size):
        count = sum(bitarray[i] for bitarray in bitarrays)
        if count >= threshold:
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


def getIndex(idSet, sender):
    for index, voter in enumerate(idSet):
        if sender == voter:
            return index
    return -1  # Return -1 if the sender is not found in the idSet


def createCommitteeBitArray(voters, committee_size):
    committee_bit_array = [False] * committee_size

    for vote in voters:
        sender = vote.sender
        index = getIndex(voters, sender)
        if index >= 0 and index < committee_size:
            committee_bit_array[index] = True

    return committee_bit_array





def merge_bitarrays(bitarray1, bitarray2):
    merged_array = bitarray1 + bitarray2
    return merged_array










