#include "CommandChannel.hpp"
#include "../ChannelEnvVars.hpp"
#include "../ChannelUtils.hpp"

#include <unistd.h>
#include <climits>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <memory>
#include <string>
#include <stdexcept>
#include <utility>

namespace thd {
namespace {

void sendMessage(int socket, std::unique_ptr<rpc::RPCMessage> msg) {
  auto& bytes = msg.get()->bytes();
  std::uint64_t msg_length = static_cast<std::uint64_t>(bytes.length());

  send_bytes<std::uint64_t>(socket, &msg_length, 1);
  send_bytes<std::uint8_t>(
    socket,
    reinterpret_cast<const std::uint8_t*>(bytes.data()),
    msg_length
  );
}

std::unique_ptr<rpc::RPCMessage> receiveMessage(int socket) {
  std::uint64_t msg_length;
  recv_bytes<std::uint64_t>(socket, &msg_length, 1);

  std::unique_ptr<std::uint8_t[]> bytes(new std::uint8_t[msg_length]);
  recv_bytes<std::uint8_t>(socket, bytes.get(), msg_length);

  return std::unique_ptr<rpc::RPCMessage>(
    new rpc::RPCMessage(reinterpret_cast<char*>(bytes.get()), msg_length)
  );
}

} // anonymous namespace

MasterCommandChannel::MasterCommandChannel()
  : _rank(0)
{
  std::uint32_t world_size;
  std::tie(_port, world_size) = load_master_env();

  _sockets.resize(world_size);
  std::fill(_sockets.begin(), _sockets.end(), -1);
}

MasterCommandChannel::~MasterCommandChannel() {
  for (auto socket : _sockets) {
    if (socket != -1)
      ::close(socket);
  }
}

bool MasterCommandChannel::init() {
  // listen on workers
  std::tie(_sockets[0], std::ignore) = listen(_port);

  int socket;
  std::uint32_t rank;
  for (std::size_t i = 1; i < _sockets.size(); ++i) {
    std::tie(socket, std::ignore) = accept(_sockets[0]);
    recv_bytes<std::uint32_t>(socket, &rank, 1);
    _sockets.at(rank) = socket;
  }

  /* Sending confirm byte is necessary to block workers until all remaing workers
   * connect. This necessesity comes from case when worker finishes connecting
   * to command channel and start connecting to data channel. Since master
   * in both channels listen on same port workers potentially could try to connect
   * data channel when master is still listening in command channel - this
   * could cause a deadlock.
   */
  for (std::size_t i = 1; i < _sockets.size(); ++i) {
    std::uint8_t confirm_byte = 1;
    send_bytes<std::uint8_t>(_sockets[i], &confirm_byte, 1);
  }

   // close listen socket
  ::close(_sockets[0]);
  _sockets[0] = -1;
  return true;
}

void MasterCommandChannel::sendMessage(std::unique_ptr<rpc::RPCMessage> msg, int rank) {
  if (rank <= 0) {
    throw std::domain_error("sendMessage received invalid rank as parameter");
  }

  ::thd::sendMessage(_sockets.at(rank), std::move(msg));
}

std::unique_ptr<rpc::RPCMessage> MasterCommandChannel::recvMessage(int rank) {
  if (rank <= 0) {
    throw std::domain_error("recvMessage received invalid rank as parameter");
  }

  return receiveMessage(_sockets.at(rank));
}


WorkerCommandChannel::WorkerCommandChannel()
  : _socket(-1)
{
  _rank = load_rank_env();
  std::tie(_master_addr, _master_port) = load_worker_env();
}

WorkerCommandChannel::~WorkerCommandChannel() {
  if (_socket != -1)
    ::close(_socket);
}

bool WorkerCommandChannel::init() {
  _socket = connect(_master_addr, _master_port);
  send_bytes<std::uint32_t>(_socket, &_rank, 1); // send rank

  std::uint8_t confirm_byte;
  recv_bytes<std::uint8_t>(_socket, &confirm_byte, 1);
  return true;
}

void WorkerCommandChannel::sendMessage(std::unique_ptr<rpc::RPCMessage> msg) {
  ::thd::sendMessage(_socket, std::move(msg));
}

std::unique_ptr<rpc::RPCMessage> WorkerCommandChannel::recvMessage() {
  return receiveMessage(_socket);
}

} // namespace thd
