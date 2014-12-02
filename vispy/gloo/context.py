# -*- coding: utf-8 -*-
# Copyright (c) 2014, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""
Functionality to deal with GL Contexts in vispy. This module is defined
in gloo, because gloo (and the layers that depend on it) need to be
context aware. The vispy.app module "provides" a context, and therefore
depends on this module. Although the GLContext class is aimed for use
by vispy.app (for practical reasons), it should be possible to use
GLContext without using vispy.app by overloading it in an appropriate
manner.

An GLContext object acts as a placeholder on which different parts
of vispy (or other systems) can keep track of information related to
an OpenGL context.
"""

from copy import deepcopy
import weakref

from .glir import GlirParser, GlirQueue
from .wrappers import BaseGlooFunctions

_default_dict = dict(red_size=8, green_size=8, blue_size=8, alpha_size=8,
                     depth_size=16, stencil_size=0, double_buffer=True,
                     stereo=False, samples=0)


canvasses = []


def get_default_config():
    """Get the default OpenGL context configuration

    Returns
    -------
    config : dict
        Dictionary of config values.
    """
    return deepcopy(_default_dict)


def get_current_canvas():
    """ Get the currently active canvas
    
    Returns None if there is no canvas available. A canvas is made
    active on initialization and before the draw event is emitted.
    
    When a gloo object is created, it is associated with the currently
    active Canvas, or with the next Canvas to be created if there is
    no current Canvas. Use Canvas.set_current() to manually activate a
    canvas.
    """
    cc = [c() for c in canvasses if c() is not None]
    if cc:
        return cc[-1]
    else:
        return None


def set_current_canvas(canvas):
    """ Make a canvas active. Used primarily by the canvas itself.
    """
    # Notify glir 
    canvas.context.glir.command('CURRENT', 0)
    # Try to be quick
    if canvasses and canvasses[-1]() is canvas:
        return
    # Make this the current
    cc = [c() for c in canvasses if c() is not None]
    while canvas in cc:
        cc.remove(canvas)
    cc.append(canvas)
    canvasses[:] = [weakref.ref(c) for c in cc]


def forget_canvas(canvas):
    """ Forget about the given canvas. Used by the canvas when closed.
    """
    cc = [c() for c in canvasses if c() is not None]
    while canvas in cc:
        cc.remove(canvas)
    canvasses[:] = [weakref.ref(c) for c in cc]


class GLContext(BaseGlooFunctions):
    """An object encapsulating data necessary for a OpenGL context.
    """
    
    def __init__(self, config=None):
        self._set_config(config)
        self._shared = None  # Set by the app backend
        self._glir = GlirQueue()
    
    def __repr__(self):
        return "<GLContext at 0x%x>" % id(self)
    
    def _set_config(self, config):
        self._config = deepcopy(_default_dict)
        self._config.update(config or {})
        # Check the config dict
        for key, val in self._config.items():
            if key not in _default_dict:
                raise KeyError('Key %r is not a valid GL config key.' % key)
            if not isinstance(val, type(_default_dict[key])):
                raise TypeError('Context value of %r has invalid type.' % key)
    
    def create_shared(self, name, ref):
        """ For the app backends to create the GLShared object.
        """
        if self._shared is not None:
            raise RuntimeError('Can only set_shared once.')
        self._shared = GLShared(name, ref)
    
    @property
    def config(self):
        """ A dictionary describing the configuration of this GL context.
        """
        return self._config
    
    @property
    def glir(self):
        """ The glir queue for the context. This queue is for objects
        that can be shared accross canvases (if they share a contex).
        """
        return self._glir
    
    @property
    def shared(self):
        """ Get the object that represents the namespace that can
        potentially be shared between multiple contexts.
        """
        return self._shared
    

class GLShared(object):
    """ Representation of a "namespace" that can be shared between
    different contexts. Instances of this class are created by the
    canvas backends.
    
    This object can be used to establish whether two contexts/canvases
    share objects, and can be used as a placeholder to store shared
    information, such as glyph atlasses.
    """
    
    def __init__(self, name, ref):
        self._name = name
        self._ref = weakref.ref(ref)
        self._glir = GlirQueue(GlirParser())  # The context holds *the* parser
    
    def __repr__(self):
        return "<GLShared of %s backend at 0x%x>" % (self.name, id(self))
    
    @property
    def glir(self):
        """ The glir queue dedicated for commands related to shared
        objects such as textures, buffers and programs.
        """
        return self._glir
    
    @property
    def name(self):
        """ The name of the canvas backend that this shared namespace is
        associated with.
        """
        return self._name
    
    @property
    def ref(self):
        """ A reference (stored internally via a weakref) to an object
        that the backend system can use to obtain the low-level
        information of the "reference context". In Vispy this will
        typically be the CanvasBackend object.
        """
        ref = self._ref()
        if ref is not None:
            return ref
        else:
            raise RuntimeError('The reference is not available')
