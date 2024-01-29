from unittest import TestCase

from mixnet.test_utils import init_robustness_mixnet_config


class TestRobustness(TestCase):
    def test_build_topology(self):
        robustness_mixnet_config = init_robustness_mixnet_config()
        topology = robustness_mixnet_config.mixnet_layer_config.topology
        topology_size = robustness_mixnet_config.topology_size

        self.assertEqual(len(topology.layers), topology_size.num_layers)
        for layer in topology.layers:
            self.assertEqual(len(layer), topology_size.num_mixnodes_per_layer)
