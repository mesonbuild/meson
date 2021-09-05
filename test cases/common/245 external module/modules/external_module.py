from mesonbuild.modules import ExtensionModule, ModuleReturnValue

class ExternalModule(ExtensionModule):
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'return_true': self.return_true,
        })

    def return_true(self, state, args, kwargs):
        return ModuleReturnValue(True, [])

def initialize(*args, **kwargs) -> ExternalModule:
    return ExternalModule(*args, **kwargs)
