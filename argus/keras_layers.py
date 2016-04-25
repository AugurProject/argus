from keras import activations
from keras.layers.core import MaskedLayer, Layer, TimeDistributedDense, TimeDistributedMerge, Activation
import keras.backend as K
import theano.tensor as T


class WeightedMean(MaskedLayer):

    input_ndim = 3

    def __init__(self, max_sentences, activation='linear', **kwargs):
        self.activation = activations.get(activation)
        self.max_sentences = max_sentences

        kwargs['input_shape'] = (self.max_sentences, 3)
        super(WeightedMean, self).__init__(**kwargs)

    def build(self):
        pass

    @property
    def output_shape(self):
        return (1,)

    def get_output(self, train=False):
        e = 1e-6  # constant used for numerical stability
        X = self.get_input(train)
        mask = X[:, :, 2]
        s = X[:, :, 0] * mask
        t = X[:, :, 1] * mask

        output = self.activation(K.sum(s * t, axis=1) / (T.sum(t, axis=-1)) + e)
        output = K.reshape(output, (-1, 1))
        return output

    def get_config(self):
        config = {'name': self.__class__.__name__,
                  'activation': self.activation.__name__}
        base_config = super(WeightedMean, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


class Reshape_(MaskedLayer):
    """Copy of keras core Reshape layer, does NOT check
    if array changes size.
    """
    def __init__(self, dims, **kwargs):
        super(Reshape_, self).__init__(**kwargs)
        self.dims = tuple(dims)

    def _fix_unknown_dimension(self, input_shape, output_shape):

        output_shape = list(output_shape)

        known, unknown = 1, None
        for index, dim in enumerate(output_shape):
            if dim < 0:
                if unknown is None:
                    unknown = index
                else:
                    raise ValueError('can only specify one unknown dimension')
            else:
                known *= dim

        return tuple(output_shape)

    @property
    def output_shape(self):
        return (self.input_shape[0],) + self._fix_unknown_dimension(self.input_shape[1:], self.dims)

    def get_output(self, train=False):
        X = self.get_input(train)
        return K.reshape(X, (-1,) + self.output_shape[1:])

    def get_config(self):
        config = {'name': self.__class__.__name__,
                  'dims': self.dims}
        base_config = super(Reshape_, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


class SumMask(Layer):
    def __init__(self, **kwargs):
        super(SumMask, self).__init__(**kwargs)

    @property
    def output_shape(self):
        return (self.input_shape[0], self.input_shape[1], 1)

    def get_output(self, train=False):
        X = self.get_input(train)
        return K.expand_dims(K.switch(K.sum(X, -1), 1, 0))

    def get_config(self):
        config = {'name': self.__class__.__name__,
                  'input_dim': self.input_dim,
                  'output_dim': self.output_dim}
        base_config = super(SumMask, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


class Avg(Layer):
    def __init__(self, **kwargs):
        super(Avg, self).__init__(**kwargs)

    @property
    def output_shape(self):
        return (self.input_shape[0], 1)

    def get_output(self, train=False):
        X = self.get_input(train)
        return K.mean(X, axis=-1)

    def get_config(self):
        config = {'name': self.__class__.__name__,
                  'input_dim': self.input_dim,
                  'output_dim': self.output_dim}
        base_config = super(Avg, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))