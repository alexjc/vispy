# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------


from .glir import GlirQueue


class GLObject(object):
    """ Generic GL object that represents an object on the GPU.
    
    When a GLObject is instantiated, it is associated with the currently
    active Canvas, or with the next Canvas to be created if there is
    no current Canvas
    """
    
    # Type of GLIR object, reset in subclasses
    _GLIR_TYPE = 'DummyGlirType'
    
    # Internal id counter to keep track of GPU objects
    _idcount = 0
    
    def __init__(self):
        """ Initialize the object in the default state """
        
        # Give this object an id
        GLObject._idcount += 1
        self._id = GLObject._idcount
        
        # Create our temporary GLIR queue in which commands can be queued
        # until we get associated with a canvas and get our final queue.
        self._glir = GlirQueue()
        #print(self._GLIR_TYPE, 'takes', self._context)
        
        # Give glir command to create GL representation of this object
        self._glir.command('CREATE', self._id, self._GLIR_TYPE)
    
    def _associate_canvas(self, canvas, first=False):
        """ This method is used to swap the temporary queue with the
        final queue of the canvas or context. This method is called in
        Program.draw() and FrameBuffer.activate(): these are the moments
        that gloo objects get associated. This method replaces itself
        with a dummy function: all calls but the first should just
        return asap. Some classes override this method to use the queue
        of the canvas rather than the context.
        """
        if self._GLIR_TYPE in ('RenderBuffer', 'FrameBuffer'):
            new_queue = canvas.context.glir
        else:
            new_queue = canvas.context.shared.glir
        new_queue.push(self._glir.clear(), first)
        self._glir = new_queue
        self._associate_canvas = lambda canvas=None, first=False: None
    
    def __del__(self):
        # You never know when this is goint to happen. The window might
        # already be closed and no OpenGL context might be available.
        # Worse, there might be multiple contexts and calling delete()
        # at the wrong moment might remove other gl objects, leading to
        # very strange and hard to debug behavior.
        #
        # So we don't do anything. If each GLObject was aware of the
        # context in which it resides, we could do auto-cleanup though...
        # todo: it's not very Pythonic to have to delete an object.
        pass

    def delete(self):
        """ Delete the object from GPU memory """
        self._glir.command('DELETE', self._id)
    
    @property
    def id(self):
        """ The id of this GL object used to reference the GL object
        in GLIR. id's are unique within a process.
        """
        return self._id
