/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 */

#pragma once

#include "gloo/algorithm.h"
#include "gloo/common/logging.h"

namespace gloo {

template <typename T>
class Broadcast : public Algorithm {
 public:
  Broadcast(const std::shared_ptr<Context>& context, int rootRank)
      : Algorithm(context), rootRank_(rootRank) {
    GLOO_ENFORCE_GE(rootRank_, 0);
    GLOO_ENFORCE_LT(rootRank_, contextSize_);
  }

  virtual ~Broadcast(){};

 protected:
  const int rootRank_;
};

} // namespace gloo
