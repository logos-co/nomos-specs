import asyncio

from node import DANode

class DANetwork:
    num_nodes: int 
    nodes: ()

    def __init__(self, nodes):   
        self.num_nodes = nodes

    async def build(self):
        node_list = []
        init_port = 7566
        for i in range(0,self.num_nodes):
            init_port += 1
            n = await DANode.new(init_port)
            try:
                await n.task
            except Exception as e:
                print("exception:")
                print(type(e))
                print(e.args)
                print(e)
            node_list.append(n)

        self.nodes = tuple(node_list)


    def get_nodes(self):
        return self.nodes

