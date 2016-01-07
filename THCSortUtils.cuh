#ifndef THC_SORT_UTILS_INC
#define THC_SORT_UTILS_INC

#include "THCReduceApplyUtils.cuh"

// Collection of kernel sort routines
template <typename T>
struct LTComp {
  __device__ inline bool operator()(const T& a, const T& b) const {
    return (a < b);
  }
};

template <typename T>
struct GTComp {
  __device__ inline bool operator()(const T& a, const T& b) const {
    return (a > b);
  }
};

template <typename T>
__device__ inline void swapVars(T& t1, T& t2) {
  T tmp = t1;
  t1 = t2;
  t2 = tmp;
}

template <typename Comparator, typename K, typename V>
__device__ inline void bitonicSwap(K& kA, V& vA, bool& validA,
                                   K& kB, V& vB, bool& validB,
                                   bool dir,
                                   const Comparator& comp) {
  // Invalid entries always sort to the end
  bool swap = (comp(kA, kB) && validA) || !validB;
  if (swap == dir) {
    swapVars(kA, kB);
    swapVars(vA, vB);
    swapVars(validA, validB);
  }
};

template <typename Comparator, typename K, typename V,
          typename IndexType, int Power2SortSize>
__device__ inline void bitonicSort(K keys[Power2SortSize],
                                   V values[Power2SortSize],
                                   bool valid[Power2SortSize],
                                   const Comparator& comp) {
#pragma unroll
  for (unsigned int size = 2; size < Power2SortSize; size *= 2) {
    bool flag = ((threadIdx.x & (size / 2)) != 0);

#pragma unroll
    for (unsigned int stride = size / 2; stride > 0; stride /= 2) {

      // Single warp per slice is completely synchronous
      if (Power2SortSize > 64) {
        __syncthreads();
      }

      unsigned int pos = 2 * threadIdx.x - (threadIdx.x & (stride - 1));
      bitonicSwap<Comparator, K, V>(
        keys[pos], values[pos], valid[pos],
        keys[pos + stride], values[pos + stride], valid[pos + stride],
        flag, comp);
    }
  }

#pragma unroll
  for (unsigned int stride = Power2SortSize / 2; stride > 0; stride /= 2) {
    // Single warp per slice is completely synchronous
    if (Power2SortSize > 64) {
      __syncthreads();
    }

    unsigned int pos = 2 * threadIdx.x - (threadIdx.x & (stride - 1));
    bitonicSwap<Comparator, K, V>(
      keys[pos], values[pos], valid[pos],
      keys[pos + stride], values[pos + stride], valid[pos + stride],
      false, comp);
  }

  // Single warp per slice is completely synchronous
  if (Power2SortSize > 64) {
    __syncthreads();
  }
}

// Sorts (key, value) pairs (in different tensors) in-place; i.e.,
// modifies the input `keys` and `values`
template <typename K, typename V,
          int KeyDims, int ValueDims,
          typename Comparator, typename IndexType, int Power2SortSize>
__global__ void
bitonicSortKVInPlace(TensorInfo<IndexType> keys,
                     IndexType keySlices,
                     IndexType keySliceSize,
                     IndexType keySliceStride,
                     TensorInfo<IndexType> values,
                     IndexType valueSliceStride,
                     const Comparator& comp) {
  // Find the slice of the tensor that we are sorting
  const IndexType linearIndex = getLinearBlockId<IndexType>();
  // Tiling the slices could have us be out of bounds, if there are a
  // lot of slices to sort
  if (linearIndex >= keySlices) {
    return;
  }

  __shared__ K sharedKeys[Power2SortSize];
  __shared__ V sharedValues[Power2SortSize];
  __shared__ bool sharedValid[Power2SortSize];

  const IndexType keyStartOffset =
    IndexToOffset<IndexType, KeyDims>::get(linearIndex, keys);
  const IndexType valueStartOffset =
    IndexToOffset<IndexType, ValueDims>::get(linearIndex, values);

  // If the sort size is 1, the data is already sorted
  if (Power2SortSize == 1) {
    return;
  } else {
    // Otherwise, each thread is responsible for loading and storing 2
    // elements. The sort size is guaranteed to be >= 2
    const int elem1 = threadIdx.x;
    const int elem2 = threadIdx.x + (Power2SortSize / 2);

    bool valid1 = (elem1 < keySliceSize);
    K k1 = valid1 ?
      keys.data[keyStartOffset + elem1 * keySliceStride] : (K) 0;
    V v1 = valid1 ?
      values.data[valueStartOffset + elem1 * valueSliceStride] : (V) 0;

    sharedKeys[elem1] = k1;
    sharedValues[elem1] = v1;
    sharedValid[elem1] = valid1;

    bool valid2 = (elem2 < keySliceSize);
    K k2 = valid2 ?
      keys.data[keyStartOffset + elem2 * keySliceStride] : (K) 0;
    V v2 = valid2 ?
      values.data[valueStartOffset + elem2 * valueSliceStride] : (V) 0;

    sharedKeys[elem2] = k2;
    sharedValues[elem2] = v2;
    sharedValid[elem2] = valid2;

    // Sort!
    bitonicSort<Comparator, K, V, IndexType, Power2SortSize>(
      sharedKeys, sharedValues, sharedValid, comp);

    // elem1 values are always valid, since otherwise we would have
    // chosen the next smallest power-of-2 for sorting
    keys.data[keyStartOffset + elem1 * keySliceStride] =
      sharedKeys[elem1];
    values.data[valueStartOffset + elem1 * valueSliceStride] =
      sharedValues[elem1];

    if (valid2) {
      // elem2 values might be out-of-range, if the data size we are
      // sorting is not a power-of-2
      keys.data[keyStartOffset + elem2 * keySliceStride] =
        sharedKeys[elem2];
      values.data[valueStartOffset + elem2 * valueSliceStride] =
        sharedValues[elem2];
    }
  }
}

#endif // THC_SORT_UTILS_INC
