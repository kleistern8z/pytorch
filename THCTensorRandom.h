#ifndef TH_CUDA_TENSOR_RANDOM_INC
#define TH_CUDA_TENSOR_RANDOM_INC

#include "THCTensor.h"

THC_API void THCRandom_init(int num_devices, int current_device);
THC_API void THCRandom_shutdown();
THC_API void THCRandom_setGenerator(int device);
THC_API unsigned long THCRandom_seed();
THC_API void THCRandom_manualSeed(unsigned long the_seed_);
THC_API unsigned long THCRandom_initialSeed();
THC_API void THCRandom_getRNGState(THByteTensor *rng_state);
THC_API void THCRandom_setRNGState(THByteTensor *rng_state);
THC_API void THCudaTensor_geometric(THCudaTensor *self, double p);
THC_API void THCudaTensor_bernoulli(THCudaTensor *self, double p);
THC_API void THCudaTensor_uniform(THCudaTensor *self, double a, double b);
THC_API void THCudaTensor_normal(THCudaTensor *self, double mean, double stdv);
THC_API void THCudaTensor_exponential(THCudaTensor *self, double lambda);
THC_API void THCudaTensor_cauchy(THCudaTensor *self, double median, double sigma);
THC_API void THCudaTensor_logNormal(THCudaTensor *self, double mean, double stdv);

#endif
