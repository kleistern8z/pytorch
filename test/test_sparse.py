import torch
from torch import sparse

import itertools
import random
import unittest
from common import TestCase, run_tests
from common_nn import TEST_CUDA
from numbers import Number


def cpu_only(inner):
    def outer(self, *args, **kwargs):
        unittest.skipIf(self.is_cuda, "Test is CPU-only")(inner)(self, *args, **kwargs)
    return outer


class TestSparse(TestCase):

    def setUp(self):
        # These parameters control the various ways we can run the test.
        # We will subclass and override this method to implement CUDA
        # tests
        self.is_cuda = False
        self.IndexTensor = torch.LongTensor
        self.ValueTensor = torch.DoubleTensor
        self.SparseTensor = torch.sparse.DoubleTensor

    def _gen_sparse(self, d, nnz, with_size):
        # TODO: Consider implementing this in the CUDA case by directly
        # performing the operations on the GPU.  You won't be able to
        # use torch.rand/torch.randn in this case because they are
        # CPU-only.  If you do this, you can remove the is_cuda branch
        # at the end.

        if isinstance(with_size, Number):
            v = torch.randn(nnz)
            i = (torch.rand(d, nnz) * with_size).type(torch.LongTensor)
            x = torch.sparse.DoubleTensor(i, v)
        else:
            # Generate a sparse tensor with d sparse dimensions; the
            # rest the dimensions with_size[d:] are dense.
            v_size = [nnz] + list(with_size[d:])
            v = torch.randn(*v_size)
            i = torch.rand(d, nnz) * \
                torch.Tensor(with_size[:d]).repeat(nnz, 1).transpose(0, 1)
            i = i.type(torch.LongTensor)
            x = torch.sparse.DoubleTensor(i, v, torch.Size(with_size))

        if self.is_cuda:
            return x.cuda(), i.cuda(), v.cuda()
        else:
            return x, i.clone(), v.clone()

    def randn(self, *args, **kwargs):
        # TODO: Maybe do this directly on GPU
        x = torch.randn(*args, **kwargs)
        if self.is_cuda:
            x = x.cuda()
        return x

    def test_basic(self):
        x, i, v = self._gen_sparse(3, 10, 100)

        self.assertEqual(i, x.indices())
        self.assertEqual(v, x.values())

        x, i, v = self._gen_sparse(3, 10, [100, 100, 100])
        self.assertEqual(i, x.indices())
        self.assertEqual(v, x.values())
        self.assertEqual(x.ndimension(), 3)
        self.assertEqual(x.nnz(), 10)
        for i in range(3):
            self.assertEqual(x.size(i), 100)

        # Make sure we can access empty indices / values
        x = self.SparseTensor()
        self.assertEqual(x.indices().numel(), 0)
        self.assertEqual(x.values().numel(), 0)

    def test_to_dense(self):
        i = self.IndexTensor([
            [0, 1, 2, 2],
            [0, 0, 0, 3],
            [0, 0, 1, 4],
        ])
        v = self.ValueTensor([2, 1, 3, 4])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 5]))
        res = self.ValueTensor([
            [[2, 0, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0]],
            [[1, 0, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0]],
            [[0, 3, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 0, 0, 4]],
        ])

        x.to_dense()  # Tests double to_dense for memory corruption
        x.to_dense()
        x.to_dense()
        self.assertEqual(res, x.to_dense())

    def test_to_dense_hybrid(self):
        i = self.IndexTensor([
            [0, 1, 2, 2],
            [0, 0, 0, 3],
        ])
        v = self.ValueTensor([[2, 3], [1, 2], [3, 4], [4, 5]])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 2]))
        res = self.ValueTensor([
            [[2, 3],
             [0, 0],
             [0, 0],
             [0, 0]],
            [[1, 2],
             [0, 0],
             [0, 0],
             [0, 0]],
            [[3, 4],
             [0, 0],
             [0, 0],
             [4, 5]],
        ])

        x.to_dense()  # Tests double to_dense for memory corruption
        x.to_dense()
        x.to_dense()
        self.assertEqual(res, x.to_dense())

    def test_contig(self):
        i = self.IndexTensor([
            [1, 0, 35, 14, 39, 6, 71, 66, 40, 27],
            [92, 31, 62, 50, 22, 65, 89, 74, 56, 34],
        ])
        v = self.ValueTensor([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        x = self.SparseTensor(i, v, torch.Size([100, 100]))
        exp_i = self.IndexTensor([
            [0, 1, 6, 14, 27, 35, 39, 40, 66, 71],
            [31, 92, 65, 50, 34, 62, 22, 56, 74, 89],
        ])
        exp_v = self.ValueTensor([2, 1, 6, 4, 10, 3, 5, 9, 8, 7])
        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

        i = self.IndexTensor([
            [2, 0, 2, 1],
            [0, 0, 3, 0],
            [1, 0, 4, 0],
        ])
        v = self.ValueTensor([3, 2, 4, 1])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 5]))
        exp_i = self.IndexTensor([
            [0, 1, 2, 2],
            [0, 0, 0, 3],
            [0, 0, 1, 4],
        ])
        exp_v = self.ValueTensor([2, 1, 3, 4])

        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

        # Duplicate indices
        i = self.IndexTensor([
            [0, 0, 2, 0],
            [0, 0, 3, 0],
            [0, 0, 4, 0],
        ])
        v = self.ValueTensor([3, 2, 4, 1])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 5]))
        exp_i = self.IndexTensor([
            [0, 2],
            [0, 3],
            [0, 4],
        ])
        exp_v = self.ValueTensor([6, 4])

        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

    def test_contig_hybrid(self):
        i = self.IndexTensor([
            [1, 0, 35, 14, 39, 6, 71, 66, 40, 27],
            [92, 31, 62, 50, 22, 65, 89, 74, 56, 34],
        ])
        v = self.ValueTensor([
            [1, 2], [2, 3], [3, 4], [4, 5], [5, 6],
            [6, 7], [7, 8], [8, 9], [9, 10], [10, 11],
        ])
        x = self.SparseTensor(i, v, torch.Size([100, 100, 2]))
        exp_i = self.IndexTensor([
            [0, 1, 6, 14, 27, 35, 39, 40, 66, 71],
            [31, 92, 65, 50, 34, 62, 22, 56, 74, 89],
        ])
        exp_v = self.ValueTensor([
            [2, 3], [1, 2], [6, 7], [4, 5], [10, 11],
            [3, 4], [5, 6], [9, 10], [8, 9], [7, 8],
        ])
        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

        i = self.IndexTensor([
            [2, 0, 2, 1],
            [0, 0, 3, 0],
            [1, 0, 4, 0],
        ])
        v = self.ValueTensor([[3, 3, 3], [2, 2, 2], [4, 4, 4], [1, 1, 1]])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 5, 3]))
        exp_i = self.IndexTensor([
            [0, 1, 2, 2],
            [0, 0, 0, 3],
            [0, 0, 1, 4],
        ])
        exp_v = self.ValueTensor([[2, 2, 2], [1, 1, 1], [3, 3, 3], [4, 4, 4]])

        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

        # Duplicate indices
        i = self.IndexTensor([
            [0, 0, 2, 0],
            [0, 0, 3, 0],
            [0, 0, 4, 0],
        ])
        v = self.ValueTensor([[3, 2, 3], [2, 1, 1], [4, 3, 4], [1, 1, 1]])
        x = self.SparseTensor(i, v, torch.Size([3, 4, 5, 3]))
        exp_i = self.IndexTensor([
            [0, 2],
            [0, 3],
            [0, 4],
        ])
        exp_v = self.ValueTensor([[6, 4, 5], [4, 3, 4]])

        x = self.safeCoalesce(x)
        self.assertEqual(exp_i, x.indices())
        self.assertEqual(exp_v, x.values())

    def test_transpose(self):
        x = self._gen_sparse(4, 20, 5)[0]
        y = x.to_dense()

        for i, j in itertools.combinations(range(4), 2):
            x = x.transpose_(i, j)
            y = y.transpose(i, j)
            self.assertEqual(x.to_dense(), y)

            x = x.transpose(i, j)
            y = y.transpose(i, j)
            self.assertEqual(x.to_dense(), y)

    @cpu_only
    def test_mm(self):
        def test_shape(di, dj, dk):
            x, _, _ = self._gen_sparse(2, 20, [di, dj])
            t = torch.randn(di, dk)
            y = torch.randn(dj, dk)
            alpha = random.random()
            beta = random.random()

            res = torch.addmm(alpha, t, beta, x, y)
            expected = torch.addmm(alpha, t, beta, x.to_dense(), y)
            self.assertEqual(res, expected)

            res = torch.addmm(t, x, y)
            expected = torch.addmm(t, x.to_dense(), y)
            self.assertEqual(res, expected)

            res = torch.mm(x, y)
            expected = torch.mm(x.to_dense(), y)
            self.assertEqual(res, expected)

        test_shape(10, 100, 100)
        test_shape(100, 1000, 200)
        test_shape(64, 10000, 300)

    @cpu_only
    def test_saddmm(self):
        def test_shape(di, dj, dk):
            x = self._gen_sparse(2, 20, [di, dj])[0]
            t = self._gen_sparse(2, 20, [di, dk])[0]
            y = torch.randn(dj, dk)
            alpha = random.random()
            beta = random.random()

            res = torch.saddmm(alpha, t, beta, x, y)
            expected = torch.addmm(alpha, t.to_dense(), beta, x.to_dense(), y)
            self.assertEqual(res.to_dense(), expected)

            res = torch.saddmm(t, x, y)
            expected = torch.addmm(t.to_dense(), x.to_dense(), y)
            self.assertEqual(res.to_dense(), expected)

            res = torch.smm(x, y)
            expected = torch.mm(x.to_dense(), y)
            self.assertEqual(res.to_dense(), expected)

        test_shape(7, 5, 3)
        test_shape(1000, 100, 100)
        test_shape(3000, 64, 300)

    def test_dsmm(self):
        def test_shape(di, dj, dk):
            x = self._gen_sparse(2, 20, [di, dj])[0]
            y = self.randn(dj, dk)

            res = torch.dsmm(x, y)
            expected = torch.mm(x.to_dense(), y)
            self.assertEqual(res, expected)

        test_shape(7, 5, 3)
        test_shape(1000, 100, 100)
        test_shape(3000, 64, 300)

    def test_hsmm(self):
        def test_shape(di, dj, dk):
            x = self._gen_sparse(2, 20, [di, dj])[0]
            y = self.randn(dj, dk)

            res = torch.hsmm(x, y)
            expected = torch.mm(x.to_dense(), y)
            self.assertEqual(res.to_dense(), expected)

        test_shape(7, 5, 3)
        test_shape(1000, 100, 100)
        test_shape(3000, 64, 300)

    def _test_spadd_shape(self, shape_i, shape_v=None):
        shape = shape_i + (shape_v or [])
        x, _, _ = self._gen_sparse(len(shape_i), 10, shape)
        y = self.randn(*shape)
        r = random.random()

        res = torch.add(y, r, x)
        expected = y + r * x.to_dense()

        self.assertEqual(res, expected)

        # Non contiguous dense tensor
        s = list(shape)
        s[0] = shape[-1]
        s[-1] = shape[0]
        y = self.randn(*s)
        y.transpose_(0, len(s) - 1)
        r = random.random()

        res = torch.add(y, r, x)
        expected = y + r * x.to_dense()

        self.assertEqual(res, expected)

    def test_spadd(self):
        self._test_spadd_shape([5, 6])
        self._test_spadd_shape([10, 10, 10])
        self._test_spadd_shape([50, 30, 20])
        self._test_spadd_shape([5, 5, 5, 5, 5, 5])

    def test_spadd_hybrid(self):
        self._test_spadd_shape([5, 6], [2, 3])
        self._test_spadd_shape([10, 10, 10], [3])
        self._test_spadd_shape([50, 30, 20], [2])
        self._test_spadd_shape([5, 5, 5, 5, 5, 5], [2])

    def _test_basic_ops_shape(self, shape_i, shape_v=None):
        shape = shape_i + (shape_v or [])
        x1, _, _ = self._gen_sparse(len(shape_i), 9, shape)
        x2, _, _ = self._gen_sparse(len(shape_i), 12, shape)

        y1 = x1 + x2
        y2 = x1.clone()
        y2.add_(x2)
        expected = x1.to_dense() + x2.to_dense()
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        y1 = x1 - x2
        y2 = x1.clone()
        y2.sub_(x2)
        expected = x1.to_dense() - x2.to_dense()
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        y1 = x1 * x2
        y2 = x1.clone()
        y2.mul_(x2)
        expected = x1.to_dense() * x2.to_dense()
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        y1 = x1 * 37.5
        y2 = x1.clone()
        y2.mul_(37.5)
        expected = x1.to_dense() * 37.5
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        y1 = x1 / 37.5
        y2 = x1.clone()
        y2.div_(37.5)
        expected = x1.to_dense() / 37.5
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        # TODO: add back inplace support
        y1 = x1 ** 2
        y2 = x1.clone()
        y2 = y2.pow(2)
        expected = x1.to_dense() ** 2
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

        y = x1.clone()
        y.zero_()
        expected = torch.zeros(x1.size())
        self.assertEqual(y.to_dense(), expected)

        self.assertFalse(x1.is_coalesced())
        y = x1.coalesce()
        z = x1.coalesce()
        self.assertFalse(x1.is_coalesced())
        self.assertTrue(y.is_coalesced())
        self.assertEqual(x1, y)
        # check that coalesce is out of place
        y.values().add_(1)
        self.assertEqual(z.values() + 1, y.values())

    def test_basic_ops(self):
        self._test_basic_ops_shape([5, 6])
        self._test_basic_ops_shape([10, 10, 10])
        self._test_basic_ops_shape([50, 30, 20])
        self._test_basic_ops_shape([5, 5, 5, 5, 5, 5])

    def test_basic_ops_hybrid(self):
        self._test_basic_ops_shape([5, 6], [2, 3])
        self._test_basic_ops_shape([10, 10, 10], [3])
        self._test_basic_ops_shape([50, 30, 20], [2])
        self._test_basic_ops_shape([5, 5, 5, 5, 5, 5], [2])

    def _test_sparse_mask_shape(self, shape_i, shape_v=None):
        shape = shape_i + (shape_v or [])
        x1, _, _ = self._gen_sparse(len(shape_i), 9, shape)
        x2, _, _ = self._gen_sparse(len(shape_i), 12, shape)

        y1 = x1 + x2
        y2 = x1.clone()
        y2.add_(x2)
        expected = x1.to_dense() + x2.to_dense()
        self.assertEqual(y1.to_dense(), expected)
        self.assertEqual(y2.to_dense(), expected)

    def _test_sparse_mask_fixed(self):
        i = self.IndexTensor([
            [1, 3, 3, 0, 4],
            [2, 1, 1, 2, 3],
        ])
        v = self.ValueTensor([1, 2, 3, 4, 5])
        x = self.SparseTensor(i, v, torch.Size([5, 4]))
        dense = self.ValueTensor([
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16],
            [17, 18, 19, 20],
        ])
        exp_v = self.ValueTensor([7, 14, 14, 3, 20])
        res = dense.sparse_mask(x)
        expected = self.SparseTensor(i, exp_v, torch.Size([5, 4]))
        self.assertEqual(res, expected)

    def test_sparse_mask(self):
        self._test_sparse_mask_fixed()

        self._test_sparse_mask_shape([5, 6])
        self._test_sparse_mask_shape([10, 10, 10])
        self._test_sparse_mask_shape([50, 30, 20])
        self._test_sparse_mask_shape([5, 5, 5, 5, 5, 5])

    def _test_sparse_mask_hybrid_fixed(self):
        i = self.IndexTensor([
            [1, 3, 3, 0, 4],
            [2, 1, 1, 2, 3],
        ])
        v = self.ValueTensor([[1, 2], [2, 3], [3, 4], [4, 5], [5, 6]])
        x = self.SparseTensor(i, v, torch.Size([5, 4, 2]))
        dense = self.ValueTensor([
            [[1, 3], [2, 2], [3, 3], [4, 2]],
            [[5, 7], [6, 7], [7, 9], [8, 9]],
            [[9, 2], [10, 4], [11, 1], [12, 3]],
            [[13, 5], [14, 1], [15, 1], [16, 6]],
            [[17, 7], [18, 2], [19, 7], [20, 1]],
        ])
        res = dense.sparse_mask(x)
        exp_v = self.ValueTensor([[7, 9], [14, 1], [14, 1], [3, 3], [20, 1]])
        expected = self.SparseTensor(i, exp_v, torch.Size([5, 4, 2]))
        self.assertEqual(res, expected)

    def test_sparse_mask_hybrid(self):
        self._test_sparse_mask_hybrid_fixed()

        self._test_sparse_mask_shape([5, 6], [2, 3])
        self._test_sparse_mask_shape([10, 10, 10], [3])
        self._test_sparse_mask_shape([50, 30, 20], [2])
        self._test_sparse_mask_shape([5, 5, 5, 5, 5, 5], [2])


@unittest.skipIf(not TEST_CUDA, 'CUDA not available')
class TestCudaSparse(TestSparse):
    def setUp(self):
        self.is_cuda = True
        self.IndexTensor = torch.cuda.LongTensor
        self.ValueTensor = torch.cuda.DoubleTensor
        self.SparseTensor = torch.cuda.sparse.DoubleTensor

if __name__ == '__main__':
    run_tests()
