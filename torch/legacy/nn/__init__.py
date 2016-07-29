from .ffi import _backends

from . import utils

from .Module import Module
from .Criterion import Criterion
from .Container import Container

from .Sequential import Sequential
from .Parallel import Parallel
from .Concat import Concat
from .DepthConcat import DepthConcat
from .ConcatTable import ConcatTable
from .JoinTable import JoinTable
from .ParallelTable import ParallelTable

from .Abs import Abs
from .AbsCriterion import AbsCriterion
from .Add import Add
from .AddConstant import AddConstant
from .BCECriterion import BCECriterion
from .BatchNormalization import BatchNormalization
from .Bilinear import Bilinear
from .CAddTable import CAddTable
from .CDivTable import CDivTable
from .CMul import CMul
from .CMulTable import CMulTable
from .CSubTable import CSubTable
from .ClassNLLCriterion import ClassNLLCriterion
from .Contiguous import Contiguous
from .Copy import Copy
from .Cosine import Cosine
from .CosineDistance import CosineDistance
from .CosineEmbeddingCriterion import CosineEmbeddingCriterion
from .CriterionTable import CriterionTable
from .CrossEntropyCriterion import CrossEntropyCriterion
from .DistKLDivCriterion import DistKLDivCriterion
from .DotProduct import DotProduct
from .Dropout import Dropout
from .ELU import ELU
from .Euclidean import Euclidean
from .Exp import Exp
from .FlattenTable import FlattenTable
from .GradientReversal import GradientReversal
from .HardShrink import HardShrink
from .HardTanh import HardTanh
from .HingeEmbeddingCriterion import HingeEmbeddingCriterion
from .Identity import Identity
from .Index import Index
from .L1Cost import L1Cost
from .L1HingeEmbeddingCriterion import L1HingeEmbeddingCriterion
from .L1Penalty import L1Penalty
from .LeakyReLU import LeakyReLU
from .Linear import Linear
from .Log import Log
from .LogSigmoid import LogSigmoid
from .LogSoftMax import LogSoftMax
from .LookupTable import LookupTable # TODO THNN expects [1,n] indices
from .MM import MM
from .MSECriterion import MSECriterion
from .MarginCriterion import MarginCriterion
from .MarginRankingCriterion import MarginRankingCriterion
from .MaskedSelect import MaskedSelect
from .Max import Max
from .Min import Min
from .MixtureTable import MixtureTable
from .Mul import Mul
from .MulConstant import MulConstant
from .MultiCriterion import MultiCriterion
from .MV import MV
from .MultiLabelMarginCriterion import MultiLabelMarginCriterion
from .MultiLabelSoftMarginCriterion import MultiLabelSoftMarginCriterion
from .MultiMarginCriterion import MultiMarginCriterion
from .Narrow import Narrow
from .NarrowTable import NarrowTable
from .Normalize import Normalize
from .PReLU import PReLU
from .Padding import Padding
from .PairwiseDistance import PairwiseDistance
from .ParallelCriterion import ParallelCriterion
from .PartialLinear import PartialLinear # TODO require LookupTable
from .Power import Power
from .RReLU import RReLU # TODO implement
from .ReLU6 import ReLU6
from .Replicate import Replicate
from .Reshape import Reshape
from .Select import Select
from .SelectTable import SelectTable
from .Sigmoid import Sigmoid
from .SmoothL1Criterion import SmoothL1Criterion
from .SoftMarginCriterion import SoftMarginCriterion
from .SoftMax import SoftMax
from .SoftMin import SoftMin
from .SoftPlus import SoftPlus
from .SoftShrink import SoftShrink
from .SoftSign import SoftSign
from .SpatialAdaptiveMaxPooling import SpatialAdaptiveMaxPooling
from .SpatialAveragePooling import SpatialAveragePooling
from .SpatialBatchNormalization import SpatialBatchNormalization
from .SpatialClassNLLCriterion import SpatialClassNLLCriterion
from .SpatialContrastiveNormalization import SpatialContrastiveNormalization
from .SpatialConvolution import SpatialConvolution
from .SpatialConvolutionLocal import SpatialConvolutionLocal
from .SpatialConvolutionMap import SpatialConvolutionMap  # TODO Fix -1 in THNN
from .SpatialCrossMapLRN import SpatialCrossMapLRN # TODO fails tests
from .SpatialDilatedConvolution import SpatialDilatedConvolution
from .SpatialDivisiveNormalization import SpatialDivisiveNormalization
from .SpatialDropout import SpatialDropout
from .SpatialFractionalMaxPooling import SpatialFractionalMaxPooling
from .SpatialFullConvolution import SpatialFullConvolution
from .SpatialFullConvolutionMap import SpatialFullConvolutionMap # TODO Fix, just like SpatialConvolutionMap
from .SpatialLPPooling import SpatialLPPooling
from .SpatialMaxPooling import SpatialMaxPooling
from .SpatialMaxUnpooling import SpatialMaxUnpooling
from .SpatialReflectionPadding import SpatialReflectionPadding
from .SpatialReplicationPadding import SpatialReplicationPadding
from .SpatialSoftMax import SpatialSoftMax
from .SpatialSubSampling import SpatialSubSampling
from .SpatialSubtractiveNormalization import SpatialSubtractiveNormalization
from .SpatialUpSamplingNearest import SpatialUpSamplingNearest
from .SpatialZeroPadding import SpatialZeroPadding
from .SplitTable import SplitTable
from .Sqrt import Sqrt
from .Square import Square
from .Squeeze import Squeeze
from .Sum import Sum
from .Tanh import Tanh
from .TanhShrink import TanhShrink
from .Threshold import Threshold
from .Transpose import Transpose
from .Unsqueeze import Unsqueeze
from .View import View
from .WeightedEuclidean import WeightedEuclidean
from .WeightedMSECriterion import WeightedMSECriterion

from .TemporalConvolution import TemporalConvolution
from .TemporalMaxPooling import TemporalMaxPooling
from .TemporalSubSampling import TemporalSubSampling

from .VolumetricAveragePooling import VolumetricAveragePooling
from .VolumetricBatchNormalization import VolumetricBatchNormalization
from .VolumetricConvolution import VolumetricConvolution
from .VolumetricDropout import VolumetricDropout
from .VolumetricFullConvolution import VolumetricFullConvolution # TODO fails tests
from .VolumetricMaxPooling import VolumetricMaxPooling
from .VolumetricMaxUnpooling import VolumetricMaxUnpooling
from .VolumetricReplicationPadding import VolumetricReplicationPadding


from .Clamp import Clamp
from .ClassSimplexCriterion import ClassSimplexCriterion
from .ReLU import ReLU
from .Mean import Mean
