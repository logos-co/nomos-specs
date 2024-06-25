from random import randint

COLS = 10 
REPLICATION_FACTOR = 4

def calculate_subnets(node_list):
    subnets = {} 
    for i,n in enumerate(node_list): 
        idx = i%COLS

        if idx not in subnets:
            subnets[idx] = []
        subnets[idx].append(n)

    listlen = len(node_list)
    i = listlen
    while i < COLS:
        subnets[i] = []
        subnets[i].append(node_list[i%listlen])
        i += 1

    if listlen < REPLICATION_FACTOR * COLS:
        for subnet in subnets:
            last = subnets[subnet][len(subnets[subnet])-1].get_id()
            idx = -1
            for j,n in enumerate(node_list):
                if n.get_id() == last:
                    idx = j+1
            while len(subnets[subnet]) < REPLICATION_FACTOR:
                if idx > len(node_list) -1:
                    idx = 0
                if node_list[idx] in subnets[subnet]:
                    idx += 1
                    continue
                subnets[subnet].append(node_list[idx])
                idx += 1
                    

    return subnets

        

