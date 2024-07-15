from datetime import datetime
from enum import Enum

import matplotlib.pyplot as plt
import pandas


class NodeState(Enum):
    """
    A state of node at a certain time.
    For now, we assume that the node cannot send and receive messages at the same time for simplicity.
    """

    SENDING = -1
    IDLE = 0
    RECEIVING = 1


class NodeStateTable:
    def __init__(self, num_nodes: int, duration_sec: int):
        # Create a table to store the state of each node at each millisecond
        self.__table = [
            [NodeState.IDLE] * (duration_sec * 1000) for _ in range(num_nodes)
        ]

    def __getitem__(self, idx: int) -> list[NodeState]:
        return self.__table[idx]

    def analyze(self):
        df = pandas.DataFrame(self.__table).transpose()
        df.columns = [f"Node-{i}" for i in range(len(self.__table))]
        # Convert NodeState enum to their integer values
        df = df.map(lambda state: state.value)
        print("==========================================")
        print("Node States of All Nodes over Time")
        print(", ".join(f"{state.name}:{state.value}" for state in NodeState))
        print("==========================================")
        print(f"{df}\n")

        csv_path = f"all_node_states_{datetime.now().isoformat(timespec="seconds")}.csv"
        df.to_csv(csv_path)
        print(f"Saved DataFrame to {csv_path}\n")

        # Count/print the number of each state for each node
        # because the df is usually too big to print
        state_counts = df.apply(pandas.Series.value_counts).fillna(0)
        print("State Counts per Node:")
        print(f"{state_counts}\n")

        # Draw a dot plot
        plt.figure(figsize=(15, 8))
        for node in df.columns:
            times = df.index
            states = df[node]
            sending_times = times[states == NodeState.SENDING.value]
            receiving_times = times[states == NodeState.RECEIVING.value]
            plt.scatter(
                sending_times,
                [node] * len(sending_times),
                color="red",
                marker="o",
                s=10,
                label="SENDING" if node == df.columns[0] else "",
            )
            plt.scatter(
                receiving_times,
                [node] * len(receiving_times),
                color="blue",
                marker="x",
                s=10,
                label="RECEIVING" if node == df.columns[0] else "",
            )
        plt.xlabel("Time")
        plt.ylabel("Node")
        plt.title("Node States Over Time")
        plt.legend(loc="upper right")
        plt.draw()
