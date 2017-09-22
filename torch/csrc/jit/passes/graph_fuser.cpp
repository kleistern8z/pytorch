#include "torch/csrc/jit/passes/graph_fuser.h"
#include <unordered_map>

namespace torch { namespace jit {

namespace {

// What is a simple mappable operator?  It is:
//    - Has an output with the same types and sizes of its input
//    - Single output
//    - Can handle non-contiguous input
//    - Produces contiguous output
// Some of these restrictions may be relaxable, but you should
// carefully read the code first, as we rely on these assumptions.
std::unordered_set<NodeKind> simple_mappable = {
  kSigmoid,
  kTanh,
  kMul,
  kAdd,
  kNeg,
  kAddConstant,
};

bool isSimpleMap(Node *node) {
  return simple_mappable.count(node->kind());
}

struct GraphFuser {
  std::shared_ptr<Graph>& graph;

  // Used to order nodes so we always consider producer-consumer fusions
  // in reverse topological order.
  // If topological_index[a] > topological_index[b] then a occurs after b.
  // Because nodes can be added to this graph during optimization, this mapping is not bijective.
  // Newly generated nodes will copy the location where they are inserted.
  std::unordered_map<Node*,size_t> topological_index;

  GraphFuser(std::shared_ptr<Graph>& graph)
  : graph(graph) {}

  bool isCuda(Node * node) {
    return node->type()->expect<TensorType>()->device() != -1;
  }

  bool isFusable(Node * node) {
    if (!node->hasType()) return false;
    if (node->kind() == kFusionGroup) return true;
    return isSimpleMap(node) && isCuda(node);
  }

  // Can this node produce an _output_ of a fusion group?
  // all Fusable nodes can do this, but additionally Concat, which normally cannot be fused
  // because it is not a simple map, can be put in a fusion group
  // as long as no items in the group read the output of concat
  bool isFusableAsExitNode(Node * node) {
    if(isFusable(node))
      return true;
    if(node->kind() != kConcat || !isCuda(node))
      return false;

    // this concat fusion only works when all the inputs are the same size
    // otherwise they cannot partipate in the same map
    auto sizes = node->inputs().at(0)->type()->expect<TensorType>()->sizes();
    for(auto i : node->inputs()) {
      if(sizes != i->type()->expect<TensorType>()->sizes()){
        return false;
      }
    }
    return true;
  }

  // necessary condition for fusion. If all of the uses of producer are consumer
  // then it is safe to merge producer into consumer, because it doesn't have any other uses
  // If there are other uses, but they occur _after_ consumer, then we can still merge in producer
  // with consumer, by rewriting those later uses to use the version of producer generated by the fused blob
  // In this case, producer becomes an output of the fusion group.
  bool allUsersAreThisConsumerOrOccurAfterIt(Node * consumer, Node * producer) {
    for(auto u : producer->uses()) {
      if(u.user != consumer && topological_index[consumer] > topological_index[u.user])
        return false;
    }
    return true;
  }
  bool allUsersAreThisConsumer(Node * consumer, Node * producer) {
    for(auto u : producer->uses()) {
      if(u.user != consumer)
        return false;
    }
    return true;
  }

  bool shouldFuse(Node * consumer, Node * producer) {
    // this handles cases where producer can be moved _into_ the fusion group of consumer.
    // TODO: extend to fusion of consumer into _producer's_ fusion blob
    // if the consumer allInputsAreThisProducer(consumer,producer)
    // we can move the consumer up into the producer.
    // but this requires better handling of merging fusion groups so it is not done now
    return isFusable(producer) && allUsersAreThisConsumerOrOccurAfterIt(consumer, producer);
  }

  // insert a producer node into a consuming fusion group.
  // DOES NOT WORK if n is a consumer of an output of the fusion group
  // returns the node _inside_ the group that represents the node
  Graph & getSubgraph(Node * n) {
    JIT_ASSERT(n->kind() == kFusionGroup);
    return *n->g(kSubgraph);
  }
  Node * mergeNodeIntoGroup(Node* group, Node * n) {
    auto & subgraph = getSubgraph(group);
    auto & inputs = group->inputs();
    // map from nodes in the surrounding graph to parameters in the fusion
    // group's subgraph that correspond to them
    std::unordered_map<Node*,Node*> inputs_map;
    size_t i = 0;
    JIT_ASSERT(group->inputs().size() == subgraph.inputs().size());
    for(auto input : group->inputs()) {
      inputs_map[input] = subgraph.inputs()[i++];
    }
    // add n's inputs to the fusion group's input list if we don't already have them
    for (auto input : n->inputs()) {
      if (inputs_map.count(input) == 0) {
        auto in_group = subgraph.addInput();
        in_group->setType(input->typeOption());
        inputs_map[input] = in_group;
        group->addInput(input);
      }
    }
    // copy n into the graph, remapping its inputs to internal nodes
    Node * in_graph = subgraph.createClone(n,[&](Node * k)-> Node* {
      return inputs_map[k];
    });
    // if n is already an input to the fusion group,
    // we need to remove it because n is now inside the fusion group
    // remapping nodes that used the input to the newly-merged node
    // n is not an input when the fusion group is empty
    auto it = std::find(inputs.begin(), inputs.end(), n);
    if(it != inputs.end()) {
      size_t p = it - inputs.begin();
      group->removeInput(p);
      subgraph.inputs()[p]->replaceAllUsesWith(in_graph);
      subgraph.eraseInput(p);
    }
    return subgraph.prependNode(in_graph);
  }

  // turn consumer node n into a fusion group with just n inside
  // to prepare for fusion and replace uses of n with the new group
  Node * createSingletonFusionGroup(Node * n) {
    auto group = graph->createFusionGroup();
    // propogate position information for the new node so we can always
    // have a valid mapping
    topological_index[group] = topological_index[n];
    group->insertBefore(n);
    Node * mergedNode = mergeNodeIntoGroup(group,n);
    getSubgraph(group).registerOutput(mergedNode);
    auto sel = graph->createSelect(group,0);
    sel->setType(n->typeOption());
    sel->insertAfter(group);
    n->replaceAllUsesWith(sel);
    n->destroy();
    return group;
  }
  void insertAfter(Node * n, Node * after) {
    n->insertAfter(after);
    topological_index[n] = topological_index[after];
  }

  void insertAt(Node ** insertion_point, Node * n) {
    insertAfter(n, *insertion_point);
    *insertion_point = n;
  }

  Node * fuse(Node * consumer, Node * producer) {
    auto group = consumer;
    if(group->kind() != kFusionGroup) {
      group = createSingletonFusionGroup(consumer);
    }
    Node * merged = mergeNodeIntoGroup(group, producer);
    // remaining uses of this producer can occur because we allow
    // fusion in cases where uses remain after the consumer
    // if these exist, re-route them to the version of producer
    // created in FusionGroup
    if(producer->uses().size() != 0) {
      size_t offset = getSubgraph(group).registerOutput(merged);
      Node * new_producer = graph->createSelect(group,offset);
      new_producer->setType(producer->typeOption());
      insertAfter(new_producer, group);
      producer->replaceAllUsesWith(new_producer);
    }
    producer->destroy();
    return group;
  }

  bool isChunk(Node * node) {
    if (node->kind() != kSplit) return false;
    // All splits have to be equal
    auto & splits = node->is(ksplit);
    for (auto s : splits)
      if (s != splits[0]) return false;
    return true;
  }

  // in places where op can be fused into a consumer but chunk is in the way
  // distribute chunk to op's operands:
  // replace a,b = chunk(op(x,y,z)) with:
  // x0,x1 = chunk(x) (x0 has a's type, x1 has b's type)
  // y0,y1 = chunk(y) (y0 has a's type, y1 has b's type)
  // z0,z1 = chunk(z) (z0 has a's type, z1 has b's type)
  // a = op(x0,y0,z0) (a,b have their same size but are now contiguous)
  // b = op(x1,y1,x1)
  //
  // NB: Chunk motion only occurs with fusable consumers, which implies
  // that there is always some other operation, e.g., a+b, that happens
  // after the chunk, and will be put into the fusion group. This is
  // important, because distributing the chunk changes the contiguity
  // of a and b, and so the results would be invalid, except that we know
  // that simple_mappable operations will restore contiguity before
  // we exit the fusion group.

  bool tryToMoveChunk(Node * consumer, Node * producer) {
    // if we are fusing a select,
    if (producer->kind() != kSelect)
      return false;
    // and the select refers to a chunk,
    auto * chunk = producer->input();
    if (!isChunk(chunk))
      return false;
    // and the thing being chunked is fusable into the consumer
    Node * producer_for_chunk = chunk->input();
    if (!isFusable(producer_for_chunk) || !allUsersAreThisConsumer(chunk,producer_for_chunk))
      return false;
    // and all uses of the chunk are in this consumer
    for (auto s : chunk->uses()) {
      for (auto u : s.user->uses()) {
        if (u.user != consumer)
          return false;
      }
    }

    // TODO: Remove this restriction if we ever need to distribute across
    // multiple return operators
    JIT_ASSERT(!producer_for_chunk->hasMultipleOutputs());

    // Make sure we lay out the nodes in the correct topological order.
    // TODO: There should be some more enshrined way to do this
    Node * insertion_point = chunk;

    // apply chunk to each of op's operands
    // chunked_inputs[input_nr][chunk_output_idx]
    //  = Node* for chunk_output_idx'th output of the chunk(inputs[input_nr])
    std::vector<std::vector<Node*>> chunked_inputs;
    for (auto input : producer_for_chunk->inputs()) {
      auto input_type = input->type()->cast<TensorType>();
      // NB: I decided not to use cloneFrom here, because if we make cloneFrom
      // copy selects one day, it is definitely not what you want here (selects
      // have different types).
      Node * input_chunk = graph->create(kSplit);
      input_chunk->setType(multiType());
      input_chunk->copyAttributes(*chunk);
      input_chunk->addInput(input);
      insertAt(&insertion_point, input_chunk);
      // TODO: Make this go away when we make helper function for
      // setting up Selects.
      size_t i = 0;
      chunked_inputs.emplace_back(); // alas, to not be C++17
      for (auto chunk_sel : chunk->outputs()) {
          auto chunk_sel_type = chunk_sel->type()->cast<TensorType>();
          Node * input_chunk_sel = graph->createSelect(input_chunk, i++);
          input_chunk_sel->setType(
            input_type->withSizesStrides(chunk_sel_type->sizes(),
                                         chunk_sel_type->strides()));
          insertAt(&insertion_point, input_chunk_sel);
          chunked_inputs.back().push_back(input_chunk_sel);
      }
    }

    // apply the op to each chunk of the chunked operands,
    // and then rewrite the graph to use them!
    for (auto chunk_sel : chunk->outputs()) {
      Node * chunked_op = graph->create(producer_for_chunk->kind());
      chunked_op->copyAttributes(*producer_for_chunk);
      // Invariant: mappable operators always produce contiguous output
      chunked_op->setType(chunk_sel->type()->cast<TensorType>()->contiguous());
      for (auto by_chunk_output_idx : chunked_inputs) {
        chunked_op->addInput(by_chunk_output_idx.at(chunk_sel->offset()));
      }
      insertAt(&insertion_point, chunked_op);
      chunk_sel->replaceAllUsesWith(chunked_op);
      // NB: Temporarily breaking the Select invariant as we clean up
      chunk_sel->destroy();
    }

    chunk->destroy();
    producer_for_chunk->destroy();
    return true;
  }

  // returns where to continue scanning
  graph_node_list::iterator scanNode(Node * consumer) {
    auto stage_guard = graph->setStageTemporary(consumer->stage());
    if(isFusableAsExitNode(consumer)) {
      // handle inputs in reverse topological order as well...
      // otherwise in f(a,a+b) it will appear a is used twice if we consider
      // the f-a fusion before the f-(a+b) fusion first.
      node_list inputs = consumer->inputs();
      for(auto i : inputs) {
        JIT_ASSERT(topological_index.count(i) > 0);
      }
      std::sort(inputs.begin(), inputs.end(), [&](Node * a, Node * b) {
        return topological_index[a] > topological_index[b];
      });
      for(auto producer : inputs) {
        // Don't fuse accross stage boundaries
        if (producer->stage() != consumer->stage()) continue;
        if(tryToMoveChunk(consumer,producer)) {
          // the chunk before this consumer was re-arranged to allow fusion,
          // we scan this consumer again to perform the fusion
          return consumer->reverseIterator();
        }
        if(shouldFuse(consumer, producer)) {
          auto fusion_group = fuse(consumer,producer);
          // after fusion, consumer moves into a FusionGroup, so inputs is no longer valid
          // so we rescan the new FusionGroup for more fusions...
          return fusion_group->reverseIterator();
        }
      }
    }
    return ++consumer->reverseIterator();
  }

  void run() {
    size_t i = 0;
    for(auto p : graph->inputs()) {
      topological_index[p] = i++;
    }
    auto nodes = graph->nodes();
    for(auto consumer : nodes) {
      topological_index[consumer] = i++;
    }
    topological_index[graph->return_node()] = i++;

    for(auto it = nodes.rbegin(); it != nodes.rend();) {
      it = scanNode(*it);
    }
  }
};

} // anonymous namespace

void FuseGraph(std::shared_ptr<Graph>& graph) {
  GraphFuser(graph).run();
}

}}
