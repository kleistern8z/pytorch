#include <TH/THStorage.h>
#include <cstdint>
#include <unordered_map>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>

#include "../../process_group/General.hpp"
#include "../../base/Tensor.hpp"
#include "../../base/Traits.hpp"
#include "../../base/storages/THStorage.hpp"
#include "../../base/tensors/THTensor.hpp"
#include "../common/Functions.hpp"
#include "../common/RPC.hpp"
#include "../master/Master.hpp"
#include "Worker.hpp"

namespace thd {
namespace worker {

namespace detail {

void sendValueToMaster(IntStorage *from, long long value) {
  std::unique_ptr<Tensor> wrapped_value = from->newTensor();
  wrapped_value->resize({1});
  dynamic_cast<IntTensor *>(wrapped_value.get())->fill(value);
  dataChannel->send(*wrapped_value, 0);
}

void sendValueToMaster(FloatStorage *from, double value) {
  std::unique_ptr<Tensor> wrapped_value = from->newTensor();
  wrapped_value->resize({1});
  dynamic_cast<FloatTensor *>(wrapped_value.get())->fill(value);
  dataChannel->send(*wrapped_value, 0);
}

Tensor* unpackRetrieveTensor(rpc::RPCMessage& message) {
  return workerTensors.at(unpackTensor(message)).get();
}

Storage* unpackRetrieveStorage(rpc::RPCMessage& message) {
  return workerStorages.at(unpackStorage(message)).get();
}

static void finalize(rpc::RPCMessage& raw_message) {
  if (raw_message.remaining() > 0)
    throw std::invalid_argument("message is too long");
}

#include "dispatch/Storage.cpp"
#include "dispatch/Tensor.cpp"
#include "dispatch/Communication.cpp"

using dispatch_fn = void (*)(rpc::RPCMessage&);
using Functions = thd::Functions;


static const std::unordered_map<std::uint16_t, dispatch_fn> functions {
    {Functions::tensorConstruct, tensorConstruct},
    {Functions::tensorConstructWithSize, tensorConstructWithSize},
    {Functions::tensorResize, tensorResize},
    {Functions::tensorResizeAs, tensorResizeAs},
    {Functions::tensorResize1d, tensorResize1d},
    {Functions::tensorResize2d, tensorResize2d},
    {Functions::tensorResize3d, tensorResize2d},
    {Functions::tensorResize4d, tensorResize2d},
    {Functions::tensorResize5d, tensorResize2d},
    {Functions::tensorSetStorage, tensorSetStorage},
    {Functions::tensorSetStorage1d, tensorSetStorage1d},
    {Functions::tensorSetStorage2d, tensorSetStorage2d},
    {Functions::tensorSetStorage3d, tensorSetStorage3d},
    {Functions::tensorSetStorage4d, tensorSetStorage4d},
    {Functions::tensorNarrow, tensorNarrow},
    {Functions::tensorSelect, tensorSelect},
    {Functions::tensorTranspose, tensorTranspose},
    {Functions::tensorUnfold, tensorUnfold},
    {Functions::tensorAdd, tensorAdd},
    {Functions::tensorFree, tensorFree},

    {Functions::storageConstruct, storageConstruct},
    {Functions::storageConstructWithSize, storageConstructWithSize},
    {Functions::storageConstructWithSize1, storageConstructWithSize1},
    {Functions::storageConstructWithSize2, storageConstructWithSize2},
    {Functions::storageConstructWithSize3, storageConstructWithSize3},
    {Functions::storageConstructWithSize4, storageConstructWithSize4},
    {Functions::storageFree, storageFree},
    {Functions::storageFree, storageResize},
    {Functions::storageFill, storageFill},

    {Functions::sendTensor, sendTensor},
    {Functions::sendStorage, sendStorage}
};

} // namespace detail

std::string execute(std::unique_ptr<rpc::RPCMessage> raw_message_ptr) {
  try {
    // TODO: unify the function id type (it's in rpc:: now)
    auto &raw_message = *raw_message_ptr;
    uint16_t fid = rpc::unpackFunctionId(raw_message);
    auto iter = detail::functions.find(fid);
    if (iter != detail::functions.end())
      (*iter->second)(raw_message);
    else
      throw std::invalid_argument(std::string("invalid function id: ") + std::to_string(fid));
    return std::string();
  } catch(std::exception& e) {
    return std::string(e.what());
  }
}

} // namespace worker
} // namespace thd
