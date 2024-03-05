from unittest import TestCase

from da.common import ChunksMatrix


class TestCommon(TestCase):

    def test_chunks_matrix_columns(self):
        matrix = ChunksMatrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        expected = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
        for c1, c2 in zip(expected, matrix.columns):
            self.assertEqual(c1, c2)
