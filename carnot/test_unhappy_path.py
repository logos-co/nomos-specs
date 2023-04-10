# Unhappy path tests

# 1:  At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
# majority of nodes or a qc higher than th highestQC held by the majority of nodes.
# Majority means more than two thirds of total number of nodes, randomly assigned to committees.


# 2: Have  consecutive view changes and verify the following state variable:
#    last_timeout_view_qc.view
#    high_qc.view
#    current_view
#    last_voted_view

# 3: Due failure consecutive condition between parent and grand parent blocks might not meet. So whenever the
# Consecutive view  condition in the try_to_commit fails, then all the blocks between the latest_committed_block and the
# grandparent (including the grandparent) must be committed in order.
# As far as I know current code only excutes the grandparent only. It should also address the case above.


# 4: Have consecutive success adding two blocks then a failure and two consecutive success + 1 failure+ 1 success
# S1 <- S2 <- F1 <- S3 <- S4 <-F2 <- S5

# At S3, S1 should be committed. At S5, S2 and S3 must be committed