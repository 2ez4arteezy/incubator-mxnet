# coding: utf-8
# pylint: disable= arguments-differ
"""Convolutional neural network layers."""
from ..block import HybridBlock
from ... import symbol
from ...base import numeric_types
from .basic_layers import Activation


def _infer_weight_shape(op_name, data_shape, kwargs):
    op = getattr(symbol, op_name)
    sym = op(symbol.var('data', shape=data_shape), **kwargs)
    return sym.infer_shape_partial()[0]


class _Conv(HybridBlock):
    """Abstract nD convolution layer (private, used as implementation base).

    This layer creates a convolution kernel that is convolved
    with the layer input to produce a tensor of outputs.
    If `use_bias` is `True`, a bias vector is created and added to the outputs.
    Finally, if `activation` is not `None`,
    it is applied to the outputs as well.

    Parameters
    ----------
    channels : int
        The dimensionality of the output space
        i.e. the number of output channels in the convolution.
    kernel_size : int or tuple/list of n ints
        Specifies the dimensions of the convolution window.
    strides: int or tuple/list of n ints,
        Specifies the strides of the convolution.
    padding : int or tuple/list of n ints,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation: int or tuple/list of n ints,
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two convolution
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str,
        Dimension ordering of data and weight. Can be 'NCW', 'NWC', 'NCHW',
        'NHWC', 'NCDHW', 'NDHWC', etc. 'N', 'C', 'H', 'W', 'D' stands for
        batch, channel, height, width and depth dimensions respectively.
        Convolution is performed over 'D', 'H', and 'W' dimensions.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias: bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer: str or `Initializer`
        Initializer for the bias vector.
    """
    def __init__(self, channels, kernel_size, strides, padding, dilation,
                 groups, layout, in_channels=0, activation=None, use_bias=True,
                 weight_initializer=None, bias_initializer='zeros',
                 op_name='Convolution', prefix=None, params=None, **kwargs):
        super(_Conv, self).__init__(prefix=prefix, params=params)
        with self.name_scope():
            self._channels = channels
            self._in_channels = in_channels
            if isinstance(strides, numeric_types):
                strides = (strides,)*len(kernel_size)
            if isinstance(padding, numeric_types):
                padding = (padding,)*len(kernel_size)
            if isinstance(dilation, numeric_types):
                dilation = (dilation,)*len(kernel_size)
            self._op_name = op_name
            self._kwargs = {
                'kernel': kernel_size, 'stride': strides, 'dilate': dilation,
                'pad': padding, 'num_filter': channels, 'num_group': groups,
                'no_bias': not use_bias, 'layout': layout}
            self._kwargs.update(kwargs)

            dshape = [0]*(len(kernel_size) + 2)
            dshape[layout.find('N')] = 1
            dshape[layout.find('C')] = in_channels
            wshapes = _infer_weight_shape(op_name, dshape, self._kwargs)
            self.weight = self.params.get('weight', shape=wshapes[1],
                                          init=weight_initializer,
                                          allow_deferred_init=True)
            if use_bias:
                self.bias = self.params.get('bias', shape=wshapes[2],
                                            init=bias_initializer,
                                            allow_deferred_init=True)
            else:
                self.bias = None

            if activation is not None:
                self.act = Activation(activation)
            else:
                self.act = None

    def hybrid_forward(self, F, x, weight, bias=None):
        if bias is None:
            act = getattr(F, self._op_name)(x, weight, **self._kwargs)
        else:
            act = getattr(F, self._op_name)(x, weight, bias, **self._kwargs)
        if self.act is not None:
            act = self.act(act)
        return act

    def _alias(self):
        return 'conv'

    def __repr__(self):
        s = '{name}({mapping}, kernel_size={kernel}, stride={stride}'
        len_kernel_size = len(self._kwargs['kernel'])
        if self._kwargs['pad'] != (0,) * len_kernel_size:
            s += ', padding={pad}'
        if self._kwargs['dilate'] != (1,) * len_kernel_size:
            s += ', dilation={dilate}'
        if hasattr(self, 'out_pad') and self.out_pad != (0,) * len_kernel_size:
            s += ', output_padding={out_pad}'.format(out_pad=self.out_pad)
        if self._kwargs['num_group'] != 1:
            s += ', groups={num_group}'
        if self.bias is None:
            s += ', bias=False'
        s += ')'
        return s.format(name=self.__class__.__name__,
                        mapping=self._channels if not self._in_channels
                        else '{0} -> {1}'.format(self._in_channels,
                                                 self._channels),
                        **self._kwargs)


class Conv1D(_Conv):
    """1D convolution layer (e.g. temporal convolution).

    This layer creates a convolution kernel that is convolved
    with the layer input over a single spatial (or temporal) dimension
    to produce a tensor of outputs.
    If `use_bias` is True, a bias vector is created and added to the outputs.
    Finally, if `activation` is not `None`,
    it is applied to the outputs as well.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.


    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 1 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 1 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 1 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 1 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout: str, default 'NCW'
        Dimension ordering of data and weight. Can be 'NCW', 'NWC', etc.
        'N', 'C', 'W' stands for batch, channel, and width (time) dimensions
        respectively. Convolution is applied on the 'W' dimension.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 3D array of shape
        (batch_size, in_channels, width) if `layout` is `NCW`.

    Output shape:
        This depends on the `layout` parameter. Output is 3D array of shape
        (batch_size, channels, out_width) if `layout` is `NCW`.
        out_width is calculated as::

            out_width = floor((width+2*padding-dilation*(kernel_size-1)-1)/stride)+1
    """
    def __init__(self, channels, kernel_size, strides=1, padding=0, dilation=1,
                 groups=1, layout='NCW', activation=None, use_bias=True,
                 weight_initializer=None, bias_initializer='zeros',
                 in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)
        assert len(kernel_size) == 1, "kernel_size must be a number or a list of 1 ints"
        super(Conv1D, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer, bias_initializer, **kwargs)


class Conv2D(_Conv):
    """2D convolution layer (e.g. spatial convolution over images).

    This layer creates a convolution kernel that is convolved
    with the layer input to produce a tensor of
    outputs. If `use_bias` is True,
    a bias vector is created and added to the outputs. Finally, if
    `activation` is not `None`, it is applied to the outputs as well.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.

    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 2 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 2 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 2 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 2 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str, default 'NCHW'
        Dimension ordering of data and weight. Can be 'NCHW', 'NHWC', etc.
        'N', 'C', 'H', 'W' stands for batch, channel, height, and width
        dimensions respectively. Convolution is applied on the 'H' and
        'W' dimensions.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 4D array of shape
        (batch_size, in_channels, height, width) if `layout` is `NCHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 4D array of shape
        (batch_size, channels, out_height, out_width) if `layout` is `NCHW`.

        out_height and out_width are calculated as::

            out_height = floor((height+2*padding[0]-dilation[0]*(kernel_size[0]-1)-1)/stride[0])+1
            out_width = floor((width+2*padding[1]-dilation[1]*(kernel_size[1]-1)-1)/stride[1])+1
    """
    def __init__(self, channels, kernel_size, strides=(1, 1), padding=(0, 0),
                 dilation=(1, 1), groups=1, layout='NCHW',
                 activation=None, use_bias=True, weight_initializer=None,
                 bias_initializer='zeros', in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)*2
        assert len(kernel_size) == 2, "kernel_size must be a number or a list of 2 ints"
        super(Conv2D, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer, bias_initializer, **kwargs)


class Conv3D(_Conv):
    """3D convolution layer (e.g. spatial convolution over volumes).

    This layer creates a convolution kernel that is convolved
    with the layer input to produce a tensor of
    outputs. If `use_bias` is `True`,
    a bias vector is created and added to the outputs. Finally, if
    `activation` is not `None`, it is applied to the outputs as well.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.

    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 3 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 3 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 3 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 3 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str, default 'NCDHW'
        Dimension ordering of data and weight. Can be 'NCDHW', 'NDHWC', etc.
        'N', 'C', 'H', 'W', 'D' stands for batch, channel, height, width and
        depth dimensions respectively. Convolution is applied on the 'D',
        'H' and 'W' dimensions.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 5D array of shape
        (batch_size, in_channels, depth, height, width) if `layout` is `NCDHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 5D array of shape
        (batch_size, channels, out_depth, out_height, out_width) if `layout` is
        `NCDHW`.

        out_depth, out_height and out_width are calculated as::

            out_depth = floor((depth+2*padding[0]-dilation[0]*(kernel_size[0]-1)-1)/stride[0])+1
            out_height = floor((height+2*padding[1]-dilation[1]*(kernel_size[1]-1)-1)/stride[1])+1
            out_width = floor((width+2*padding[2]-dilation[2]*(kernel_size[2]-1)-1)/stride[2])+1
    """
    def __init__(self, channels, kernel_size, strides=(1, 1, 1), padding=(0, 0, 0),
                 dilation=(1, 1, 1), groups=1, layout='NCDHW', activation=None,
                 use_bias=True, weight_initializer=None, bias_initializer='zeros',
                 in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)*3
        assert len(kernel_size) == 3, "kernel_size must be a number or a list of 3 ints"
        super(Conv3D, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer, bias_initializer, **kwargs)


class Conv1DTranspose(_Conv):
    """Transposed 1D convolution layer (sometimes called Deconvolution).

    The need for transposed convolutions generally arises
    from the desire to use a transformation going in the opposite direction
    of a normal convolution, i.e., from something that has the shape of the
    output of some convolution to something that has the shape of its input
    while maintaining a connectivity pattern that is compatible with
    said convolution.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.

    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 3 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 3 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 3 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 3 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str, default 'NCW'
        Dimension ordering of data and weight. Can be 'NCW', 'NWC', etc.
        'N', 'C', 'W' stands for batch, channel, and width (time) dimensions
        respectively. Convolution is applied on the 'W' dimension.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 3D array of shape
        (batch_size, in_channels, width) if `layout` is `NCW`.

    Output shape:
        This depends on the `layout` parameter. Output is 3D array of shape
        (batch_size, channels, out_width) if `layout` is `NCW`.

        out_width is calculated as::

            out_width = (width-1)*strides-2*padding+kernel_size+output_padding
    """
    def __init__(self, channels, kernel_size, strides=1, padding=0, output_padding=0,
                 dilation=1, groups=1, layout='NCW', activation=None, use_bias=True,
                 weight_initializer=None, bias_initializer='zeros',
                 in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)
        if isinstance(output_padding, numeric_types):
            output_padding = (output_padding,)
        assert len(kernel_size) == 1, "kernel_size must be a number or a list of 1 ints"
        assert len(output_padding) == 1, "output_padding must be a number or a list of 1 ints"
        super(Conv1DTranspose, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer,
            bias_initializer, op_name='Deconvolution', adj=output_padding, **kwargs)
        self.outpad = output_padding


class Conv2DTranspose(_Conv):
    """Transposed 2D convolution layer (sometimes called Deconvolution).

    The need for transposed convolutions generally arises
    from the desire to use a transformation going in the opposite direction
    of a normal convolution, i.e., from something that has the shape of the
    output of some convolution to something that has the shape of its input
    while maintaining a connectivity pattern that is compatible with
    said convolution.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.


    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 3 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 3 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 3 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 3 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str, default 'NCHW'
        Dimension ordering of data and weight. Can be 'NCHW', 'NHWC', etc.
        'N', 'C', 'H', 'W' stands for batch, channel, height, and width
        dimensions respectively. Convolution is applied on the 'H' and
        'W' dimensions.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 4D array of shape
        (batch_size, in_channels, height, width) if `layout` is `NCHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 4D array of shape
        (batch_size, channels, out_height, out_width) if `layout` is `NCHW`.

        out_height and out_width are calculated as::

            out_height = (height-1)*strides[0]-2*padding[0]+kernel_size[0]+output_padding[0]
            out_width = (width-1)*strides[1]-2*padding[1]+kernel_size[1]+output_padding[1]
    """
    def __init__(self, channels, kernel_size, strides=(1, 1), padding=(0, 0),
                 output_padding=(0, 0), dilation=(1, 1), groups=1, layout='NCHW',
                 activation=None, use_bias=True, weight_initializer=None,
                 bias_initializer='zeros', in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)*2
        if isinstance(output_padding, numeric_types):
            output_padding = (output_padding,)*2
        assert len(kernel_size) == 2, "kernel_size must be a number or a list of 2 ints"
        assert len(output_padding) == 2, "output_padding must be a number or a list of 2 ints"
        super(Conv2DTranspose, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer,
            bias_initializer, op_name='Deconvolution', adj=output_padding, **kwargs)
        self.outpad = output_padding


class Conv3DTranspose(_Conv):
    """Transposed 3D convolution layer (sometimes called Deconvolution).

    The need for transposed convolutions generally arises
    from the desire to use a transformation going in the opposite direction
    of a normal convolution, i.e., from something that has the shape of the
    output of some convolution to something that has the shape of its input
    while maintaining a connectivity pattern that is compatible with
    said convolution.

    If `in_channels` is not specified, `Parameter` initialization will be
    deferred to the first time `forward` is called and `in_channels` will be
    inferred from the shape of input data.


    Parameters
    ----------
    channels : int
        The dimensionality of the output space, i.e. the number of output
        channels (filters) in the convolution.
    kernel_size :int or tuple/list of 3 int
        Specifies the dimensions of the convolution window.
    strides : int or tuple/list of 3 int,
        Specify the strides of the convolution.
    padding : int or a tuple/list of 3 int,
        If padding is non-zero, then the input is implicitly zero-padded
        on both sides for padding number of points
    dilation : int or tuple/list of 3 int
        Specifies the dilation rate to use for dilated convolution.
    groups : int
        Controls the connections between inputs and outputs.
        At groups=1, all inputs are convolved to all outputs.
        At groups=2, the operation becomes equivalent to having two conv
        layers side by side, each seeing half the input channels, and producing
        half the output channels, and both subsequently concatenated.
    layout : str, default 'NCDHW'
        Dimension ordering of data and weight. Can be 'NCDHW', 'NDHWC', etc.
        'N', 'C', 'H', 'W', 'D' stands for batch, channel, height, width and
        depth dimensions respectively. Convolution is applied on the 'D',
        'H', and 'W' dimensions.
    in_channels : int, default 0
        The number of input channels to this layer. If not specified,
        initialization will be deferred to the first time `forward` is called
        and `in_channels` will be inferred from the shape of input data.
    activation : str
        Activation function to use. See :func:`~mxnet.ndarray.Activation`.
        If you don't specify anything, no activation is applied
        (ie. "linear" activation: `a(x) = x`).
    use_bias : bool
        Whether the layer uses a bias vector.
    weight_initializer : str or `Initializer`
        Initializer for the `weight` weights matrix.
    bias_initializer : str or `Initializer`
        Initializer for the bias vector.


    Input shape:
        This depends on the `layout` parameter. Input is 5D array of shape
        (batch_size, in_channels, depth, height, width) if `layout` is `NCDHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 5D array of shape
        (batch_size, channels, out_depth, out_height, out_width) if `layout` is `NCDHW`.
        out_depth, out_height and out_width are calculated as::

            out_depth = (depth-1)*strides[0]-2*padding[0]+kernel_size[0]+output_padding[0]
            out_height = (height-1)*strides[1]-2*padding[1]+kernel_size[1]+output_padding[1]
            out_width = (width-1)*strides[2]-2*padding[2]+kernel_size[2]+output_padding[2]
    """
    def __init__(self, channels, kernel_size, strides=(1, 1, 1), padding=(0, 0, 0),
                 output_padding=(0, 0, 0), dilation=(1, 1, 1), groups=1, layout='NCDHW',
                 activation=None, use_bias=True, weight_initializer=None,
                 bias_initializer='zeros', in_channels=0, **kwargs):
        if isinstance(kernel_size, numeric_types):
            kernel_size = (kernel_size,)*3
        if isinstance(output_padding, numeric_types):
            output_padding = (output_padding,)*3
        assert len(kernel_size) == 3, "kernel_size must be a number or a list of 3 ints"
        assert len(output_padding) == 3, "output_padding must be a number or a list of 3 ints"
        super(Conv3DTranspose, self).__init__(
            channels, kernel_size, strides, padding, dilation, groups, layout,
            in_channels, activation, use_bias, weight_initializer, bias_initializer,
            op_name='Deconvolution', adj=output_padding, **kwargs)
        self.outpad = output_padding


class _Pooling(HybridBlock):
    """Abstract class for different pooling layers."""
    def __init__(self, pool_size, strides, padding, ceil_mode, global_pool,
                 pool_type, **kwargs):
        super(_Pooling, self).__init__(**kwargs)
        if strides is None:
            strides = pool_size
        if isinstance(strides, numeric_types):
            strides = (strides,)*len(pool_size)
        if isinstance(padding, numeric_types):
            padding = (padding,)*len(pool_size)
        self._kwargs = {
            'kernel': pool_size, 'stride': strides, 'pad': padding,
            'global_pool': global_pool, 'pool_type': pool_type,
            'pooling_convention': 'full' if ceil_mode else 'valid'}

    def hybrid_forward(self, F, x):
        return F.Pooling(x, **self._kwargs)

    def __repr__(self):
        s = '{name}(size={kernel}, stride={stride}, padding={pad}, ceil_mode={ceil_mode})'
        return s.format(name=self.__class__.__name__,
                        ceil_mode=self._kwargs['pooling_convention'] == 'full',
                        **self._kwargs)


class MaxPool1D(_Pooling):
    """Max pooling operation for one dimensional data.


    Parameters
    ----------
    pool_size: int
        Size of the max pooling windows.
    strides: int, or None
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCW'
        Dimension ordering of data and weight. Can be 'NCW', 'NWC', etc.
        'N', 'C', 'W' stands for batch, channel, and width (time) dimensions
        respectively. Pooling is applied on the W dimension.
    ceil_mode : bool, default False
        When `True`, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 3D array of shape
        (batch_size, channels, width) if `layout` is `NCW`.

    Output shape:
        This depends on the `layout` parameter. Output is 3D array of shape
        (batch_size, channels, out_width) if `layout` is `NCW`.

        out_width is calculated as::

            out_width = floor((width+2*padding-pool_size)/strides)+1

        When `ceil_mode` is `True`, ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=2, strides=None, padding=0, layout='NCW',
                 ceil_mode=False, **kwargs):
        assert layout == 'NCW', "Only supports NCW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)
        assert len(pool_size) == 1, "pool_size must be a number or a list of 1 ints"
        super(MaxPool1D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'max', **kwargs)


class MaxPool2D(_Pooling):
    """Max pooling operation for two dimensional (spatial) data.


    Parameters
    ----------
    pool_size: int or list/tuple of 2 ints,
        Size of the max pooling windows.
    strides: int, list/tuple of 2 ints, or None.
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int or list/tuple of 2 ints,
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCHW'
        Dimension ordering of data and weight. Can be 'NCHW', 'NHWC', etc.
        'N', 'C', 'H', 'W' stands for batch, channel, height, and width
        dimensions respectively. padding is applied on 'H' and 'W' dimension.
    ceil_mode : bool, default False
        When `True`, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 4D array of shape
        (batch_size, channels, height, width) if `layout` is `NCHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 4D array of shape
        (batch_size, channels, out_height, out_width)  if `layout` is `NCHW`.

        out_height and out_width are calculated as::

            out_height = floor((height+2*padding[0]-pool_size[0])/strides[0])+1
            out_width = floor((width+2*padding[1]-pool_size[1])/strides[1])+1

        When `ceil_mode` is `True`, ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=(2, 2), strides=None, padding=0, layout='NCHW',
                 ceil_mode=False, **kwargs):
        assert layout == 'NCHW', "Only supports NCHW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)*2
        assert len(pool_size) == 2, "pool_size must be a number or a list of 2 ints"
        super(MaxPool2D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'max', **kwargs)


class MaxPool3D(_Pooling):
    """Max pooling operation for 3D data (spatial or spatio-temporal).


    Parameters
    ----------
    pool_size: int or list/tuple of 3 ints,
        Size of the max pooling windows.
    strides: int, list/tuple of 3 ints, or None.
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int or list/tuple of 3 ints,
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCDHW'
        Dimension ordering of data and weight. Can be 'NCDHW', 'NDHWC', etc.
        'N', 'C', 'H', 'W', 'D' stands for batch, channel, height, width and
        depth dimensions respectively. padding is applied on 'D', 'H' and 'W'
        dimension.
    ceil_mode : bool, default False
        When `True`, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 5D array of shape
        (batch_size, channels, depth, height, width) if `layout` is `NCDHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 5D array of shape
        (batch_size, channels, out_depth, out_height, out_width) if `layout`
        is `NCDHW`.

        out_depth, out_height and out_width are calculated as ::

            out_depth = floor((depth+2*padding[0]-pool_size[0])/strides[0])+1
            out_height = floor((height+2*padding[1]-pool_size[1])/strides[1])+1
            out_width = floor((width+2*padding[2]-pool_size[2])/strides[2])+1

        When `ceil_mode` is `True`, ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=(2, 2, 2), strides=None, padding=0,
                 ceil_mode=False, layout='NCDHW', **kwargs):
        assert layout == 'NCDHW', "Only supports NCDHW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)*3
        assert len(pool_size) == 3, "pool_size must be a number or a list of 3 ints"
        super(MaxPool3D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'max', **kwargs)


class AvgPool1D(_Pooling):
    """Average pooling operation for temporal data.

    Parameters
    ----------
    pool_size: int
        Size of the max pooling windows.
    strides: int, or None
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCW'
        Dimension ordering of data and weight. Can be 'NCW', 'NWC', etc.
        'N', 'C', 'W' stands for batch, channel, and width (time) dimensions
        respectively. padding is applied on 'W' dimension.
    ceil_mode : bool, default False
        When `True`, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 3D array of shape
        (batch_size, channels, width) if `layout` is `NCW`.

    Output shape:
        This depends on the `layout` parameter. Output is 3D array of shape
        (batch_size, channels, out_width) if `layout` is `NCW`.

        out_width is calculated as::

            out_width = floor((width+2*padding-pool_size)/strides)+1

        When `ceil_mode` is `True`, ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=2, strides=None, padding=0, layout='NCW',
                 ceil_mode=False, **kwargs):
        assert layout == 'NCW', "Only supports NCW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)
        assert len(pool_size) == 1, "pool_size must be a number or a list of 1 ints"
        super(AvgPool1D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'avg', **kwargs)


class AvgPool2D(_Pooling):
    """Average pooling operation for spatial data.

    Parameters
    ----------
    pool_size: int or list/tuple of 2 ints,
        Size of the max pooling windows.
    strides: int, list/tuple of 2 ints, or None.
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int or list/tuple of 2 ints,
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCHW'
        Dimension ordering of data and weight. Can be 'NCHW', 'NHWC', etc.
        'N', 'C', 'H', 'W' stands for batch, channel, height, and width
        dimensions respectively. padding is applied on 'H' and 'W' dimension.
    ceil_mode : bool, default False
        When True, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 4D array of shape
        (batch_size, channels, height, width) if `layout` is `NCHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 4D array of shape
        (batch_size, channels, out_height, out_width)  if `layout` is `NCHW`.

        out_height and out_width are calculated as::

            out_height = floor((height+2*padding[0]-pool_size[0])/strides[0])+1
            out_width = floor((width+2*padding[1]-pool_size[1])/strides[1])+1

        When `ceil_mode` is `True`, ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=(2, 2), strides=None, padding=0,
                 ceil_mode=False, layout='NCHW', **kwargs):
        assert layout == 'NCHW', "Only supports NCHW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)*2
        assert len(pool_size) == 2, "pool_size must be a number or a list of 2 ints"
        super(AvgPool2D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'avg', **kwargs)


class AvgPool3D(_Pooling):
    """Average pooling operation for 3D data (spatial or spatio-temporal).

    Parameters
    ----------
    pool_size: int or list/tuple of 3 ints,
        Size of the max pooling windows.
    strides: int, list/tuple of 3 ints, or None.
        Factor by which to downscale. E.g. 2 will halve the input size.
        If `None`, it will default to `pool_size`.
    padding: int or list/tuple of 3 ints,
        If padding is non-zero, then the input is implicitly
        zero-padded on both sides for padding number of points.
    layout : str, default 'NCDHW'
        Dimension ordering of data and weight. Can be 'NCDHW', 'NDHWC', etc.
        'N', 'C', 'H', 'W', 'D' stands for batch, channel, height, width and
        depth dimensions respectively. padding is applied on 'D', 'H' and 'W'
        dimension.
    ceil_mode : bool, default False
        When True, will use ceil instead of floor to compute the output shape.


    Input shape:
        This depends on the `layout` parameter. Input is 5D array of shape
        (batch_size, channels, depth, height, width) if `layout` is `NCDHW`.

    Output shape:
        This depends on the `layout` parameter. Output is 5D array of shape
        (batch_size, channels, out_depth, out_height, out_width) if `layout`
        is `NCDHW`.

        out_depth, out_height and out_width are calculated as ::

            out_depth = floor((depth+2*padding[0]-pool_size[0])/strides[0])+1
            out_height = floor((height+2*padding[1]-pool_size[1])/strides[1])+1
            out_width = floor((width+2*padding[2]-pool_size[2])/strides[2])+1

        When `ceil_mode` is `True,` ceil will be used instead of floor in this
        equation.
    """
    def __init__(self, pool_size=(2, 2, 2), strides=None, padding=0,
                 ceil_mode=False, layout='NCDHW', **kwargs):
        assert layout == 'NCDHW', "Only supports NCDHW layout for now"
        if isinstance(pool_size, numeric_types):
            pool_size = (pool_size,)*3
        assert len(pool_size) == 3, "pool_size must be a number or a list of 3 ints"
        super(AvgPool3D, self).__init__(
            pool_size, strides, padding, ceil_mode, False, 'avg', **kwargs)


class GlobalMaxPool1D(_Pooling):
    """Global max pooling operation for temporal data."""
    def __init__(self, layout='NCW', **kwargs):
        assert layout == 'NCW', "Only supports NCW layout for now"
        super(GlobalMaxPool1D, self).__init__(
            (1,), None, 0, True, True, 'max', **kwargs)


class GlobalMaxPool2D(_Pooling):
    """Global max pooling operation for spatial data."""
    def __init__(self, layout='NCHW', **kwargs):
        assert layout == 'NCHW', "Only supports NCW layout for now"
        super(GlobalMaxPool2D, self).__init__(
            (1, 1), None, 0, True, True, 'max', **kwargs)

class GlobalMaxPool3D(_Pooling):
    """Global max pooling operation for 3D data."""
    def __init__(self, layout='NCDHW', **kwargs):
        assert layout == 'NCDHW', "Only supports NCW layout for now"
        super(GlobalMaxPool3D, self).__init__(
            (1, 1, 1), None, 0, True, True, 'max', **kwargs)


class GlobalAvgPool1D(_Pooling):
    """Global average pooling operation for temporal data."""
    def __init__(self, layout='NCW', **kwargs):
        assert layout == 'NCW', "Only supports NCW layout for now"
        super(GlobalAvgPool1D, self).__init__(
            (1,), None, 0, True, True, 'avg', **kwargs)


class GlobalAvgPool2D(_Pooling):
    """Global average pooling operation for spatial data."""
    def __init__(self, layout='NCHW', **kwargs):
        assert layout == 'NCHW', "Only supports NCW layout for now"
        super(GlobalAvgPool2D, self).__init__(
            (1, 1), None, 0, True, True, 'avg', **kwargs)


class GlobalAvgPool3D(_Pooling):
    """Global max pooling operation for 3D data."""
    def __init__(self, layout='NCDHW', **kwargs):
        assert layout == 'NCDHW', "Only supports NCW layout for now"
        super(GlobalAvgPool3D, self).__init__(
            (1, 1, 1), None, 0, True, True, 'avg', **kwargs)
