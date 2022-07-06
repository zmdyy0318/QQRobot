
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BeanContainer:
    def __init__(self):
        self.beans = {}

    def register(self, bean):
        self.beans[type(bean)] = bean

    def get_bean(self, c):
        if c in self.beans:
            return self.beans[c]
        else:
            return None
