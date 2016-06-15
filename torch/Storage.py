class RealStorage(RealStorageBase):
    def __str__(self):
        content = ' ' + '\n '.join(str(self[i]) for i in range(len(self)))
        return content + '\n[torch.RealStorage of size {}]'.format(len(self))

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter(map(lambda i: self[i], range(self.size())))

    def tolist(self):
        return [v for v in self]
