from ..stochastic_function import StochasticFunction

# Gradient formulas are based on Simple Statistical Gradient-Following
# Algorithms for Connectionist Reinforcement Learning, available at
# http://incompleteideas.net/sutton/williams-92.pdf


class Multinomial(StochasticFunction):

    def __init__(self, num_samples):
        super(Multinomial, self).__init__()
        self.num_samples = num_samples

    def forward(self, probs):
        samples = probs.multinomial(self.num_samples)
        self.save_for_backward(probs, samples)
        self.mark_non_differentiable(samples)
        return samples

    def backward(self, reward):
        probs, samples = self.saved_tensors
        grad_probs = probs.new().resize_as_(probs).zero_()
        output_probs = probs.index_select(0, samples)
        output_probs.add_(1e-6).cinv_()
        output_probs.neg_().mul_(reward)
        grad_probs.index_add_(0, samples, output_probs)
        return grad_probs


class Bernoulli(StochasticFunction):

    def forward(self, probs):
        samples = probs.new().resize_as_(probs).bernoulli_(probs)
        self.save_for_backward(probs, samples)
        self.mark_non_differentiable(samples)
        return samples

    def backward(self, reward):
        probs, samples = self.saved_tensors
        rev_probs = probs.neg().add_(1)
        return (probs - samples) / (probs * rev_probs + 1e-6) * reward


class Normal(StochasticFunction):

    def __init__(self, stddev=None):
        super(Normal, self).__init__()
        self.stddev = stddev
        assert stddev is None or stddev > 0

    def forward(self, means, stddevs=None):
        output = means.new().resize_as_(means)
        output.normal_()
        if self.stddev is not None:
            output.mul_(self.stddev)
        elif stddevs is not None:
            output.mul_(stddevs)
        else:
            raise RuntimeError("Normal function requires specifying a common "
                "stddev, or per-sample stddev")
        output.add_(means)
        self.save_for_backward(output, means, stddevs)
        self.mark_non_differentiable(output)
        return output

    def backward(self, reward):
        output, means, stddevs = self.saved_tensors
        grad_stddevs = None
        grad_means = means - output # == -(output - means)
        assert self.stddev is not None or stddevs is not None
        if self.stddev is not None:
            grad_means /= 1e-6 + self.stddev ** 2
        else:
            stddevs_sq = stddevs * stddevs
            stddevs_cb = stddevs_sq * stddevs
            stddevs_sq += 1e-6
            stddevs_cb += 1e-6
            grad_stddevs = (grad_means * grad_means) / stddevs_cb
            grad_stddevs = (stddevs - grad_stddevs) * reward
            grad_means /= stddevs_sq
        grad_means *= reward
        return grad_means, grad_stddevs

