import torch
from torch.legacy import nn

class Copy(nn.Module):

    def __init__(self, intype, outtype, dontCast=False):
        self.dontCast = dontCast
        super(Copy, self).__init__()
        self.gradInput = intype()
        self.output = outtype()

    def updateOutput(self, input):
        self.output.resize(input.size()).copy(input)
        return self.output


    def updateGradInput(self, input, gradOutput):
        self.gradInput.resize(gradOutput.size()).copy(gradOutput)
        return self.gradInput


    def type(self, type=None, tensorCache=None):
        if type and self.dontCast:
           return self

        return super(Copy, self).type(self, type, tensorCache)

