from datetime import datetime
from enum import Enum

import pandas


class NodeState(Enum):
    SENDING = -1
    IDLE = 0
    RECEIVING = 1


class AllNodeStates:
    _table: list[list[NodeState]]

    def __init__(self, num_nodes: int, duration_sec: int):
        self._table = [
            [NodeState.IDLE] * (duration_sec * 1000) for _ in range(num_nodes)
        ]

    def __getitem__(self, idx: int) -> list[NodeState]:
        return self._table[idx]

    def analyze(self):
        df = pandas.DataFrame(self._table).transpose()
        df.columns = [f"Node-{i}" for i in range(len(self._table))]
        # Convert NodeState enum to their integer values for analysis
        df = df.map(lambda state: state.value)
        print(df)

        csv_path = f"all_node_states_{datetime.now().isoformat(timespec="seconds")}.csv"
        df.to_csv(csv_path)
        print(f"\nSaved DataFrame to {csv_path}\n")

        # 1. Count the number of each state for each node
        state_counts = df.apply(pandas.Series.value_counts).fillna(0)

        # 2. Calculate the percentage of each state for each node
        state_percentages = state_counts.div(state_counts.sum(axis=0), axis=1) * 100

        print("State Counts per Node:")
        print(state_counts)
        print("\nState Percentages per Node:")
        print(state_percentages)
