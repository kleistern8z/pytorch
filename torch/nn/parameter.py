from torch.autograd import Variable

class Parameter(Variable):

    def __init__(self, data, requires_grad=True):
        super(Parameter, self).__init__(data, requires_grad=requires_grad)

