def merge_committees(committees):
    num_committees = len(committees)
    merged_committees = []

    # Sort the committees by size
    sorted_committees = sorted(committees, key=len)

    # Divide the committees into two groups: smaller and larger
    smaller_committees = sorted_committees[:num_committees // 2]
    larger_committees = sorted_committees[num_committees // 2:]

    # Merge smaller and larger committees pairwise
    for smaller, larger in zip(smaller_committees, larger_committees):
        merged_committee = set(smaller)
        merged_committee.update(larger)
        merged_committees.append(merged_committee)

    # Handle the leftover committee, if it exists
    if num_committees % 2 == 1:
        leftover_committee = set(sorted_committees[-1])
        num_merged_committees = len(merged_committees)

        # Distribute leftover members evenly among merged committees
        for member in leftover_committee:
            # Find the index of the merged committee with the smallest size
            smallest_idx = min(range(num_merged_committees), key=lambda i: len(merged_committees[i]))
            merged_committees[smallest_idx].add(member)

    return merged_committees