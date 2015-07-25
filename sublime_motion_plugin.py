'''
TODO:
1. visual mode selection from current pointer to mark. DONE
2. redraw in case multiple LABELS start with the same letter. DONE
3. Currently, in multiple cursor mode, we can only choose one mark at a time.
    I'd like to refresh the panel to select multiple marks. Like choose a range
    of marks like [1-3] or provide a list of marks to select. May have issue
    with single and double char marks.
4. change tuple to namedtuple
a. two char label will overwrite the CRLF if the word at label is shorter than the label

6. there is only one view, not multiple view. all the view need to be self.view.
    class LabelObject has view and get all views. all that needs to go away.
    there may be a function later to deal with views in different panel
    Like drawing stuff in different views

7. Redraw doesn't have to undo then replace again with a small subset. redraw can be about changing the scope of everything else and leave the subset at the current scope
'''

import sublime
import sublime_plugin

from .motion import LabelObject

from .motion import BufferUndoCommand
from .motion import AddLabelsCommand
from .motion import JumpToLabelCommand
from .motion import draw_labels
from .motion import label_generator_singledouble


class SublimeMotionCommand(sublime_plugin.TextCommand):

    def init_settings(self,edit,*kargs,**kwargs):
        self.undo=False
        self.matched_region = None
        self.labels = LabelObject()
        self.label_gen = label_generator_singledouble()
        self.edit=edit

        self.scopes = ('invalid','comment')
        self.keys = ('focus','unfocus')
        self.unfocus_flag = sublime.DRAW_NO_FILL

        # panel variables
        self.panel_init_text = ''
        self.panel_name = 'Jump To'
        self.max_panel_len = 2

        # available mode:[anything,above,below,right,left,char,word]
        self.mode="anything"
        self.regex = r'\b[^\W]'
        self.multiple_selection = False
        self.select_till = False

        #setting the variables from the key-map
        for setting in kwargs:
            if hasattr(self,setting):
                setattr(self,setting,kwargs[setting])


    def run(self,edit,*kargs,**kwargs):

        self.init_settings(edit,*kargs,**kwargs)

        self.matched_region = None
        if self.mode in ['char','word']:
            self.label_add_special()
            self.labels_adder()
            self.show_panel(self.panel_name+' '+self.mode.capitalize(),
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)
        else:
            self.labels_adder()
            self.show_panel(self.panel_name+' '+self.mode.capitalize(),
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)


    def show_panel(self,name, init_text, done=None, change=None, cancel=None):
        self.view.window().show_input_panel(name, init_text,
                                     done, change, cancel)

    def on_panel_done(self, input):
        self.matched_region = self.labels.get_region_by_label(input)
        self.undobuffer_and_jump()

    def on_panel_change(self, input):
        if len(input)>self.max_panel_len:
            self.terminate_panel()

        if not input:
            ''' for blank input, draw all labels '''
            draw_labels(self.view,self.keys,
                self.scopes,self.labels,
                self.unfocus_flag)
        else:
            # if matched and multiple focuses then draw the focus labels
            # if matched and don't refocus then jump
            # if don't match and don't refocus, then terminate
            multiple_focuses, self.matched_region = draw_labels(self.view,self.keys,self.scopes,
                                                        self.labels,self.unfocus_flag,input)

            if self.matched_region and not multiple_focuses:
                self.terminate_panel()
                self.undobuffer_and_jump()


    def on_panel_cancel(self):
        print('in change')
        self.labels.clear()
        if not self.undo:
            self.undo = BufferUndoCommand(self.view,self.edit,self.keys)

    def undobuffer_and_jump(self):
        if not self.undo:
            self.undo = BufferUndoCommand(self.view,self.edit,self.keys)
        if self.matched_region:
            JumpToLabelCommand(self.view,self.edit,self.keys, 
                    self.matched_region.begin(),
                    self.multiple_selection, self.select_till)

    def terminate_panel(self):
        self.view.window().run_command("hide_panel", {"cancel": True})


    def labels_adder(self):
        self.labels.clear()

        cursor = self.view.sel()[0].begin()

        literal = False
        beg = end = None

        if self.mode == 'above':
            beg = None
            end = cursor
        elif self.mode == 'below':
            beg = cursor
            end = None
        elif self.mode == 'left':
            beg = self.view.line(cursor).begin()
            end = cursor
        elif self.mode == 'right':
            beg = cursor
            end = self.view.line(cursor).end()
        elif self.mode == 'char':
            literal = True
        else:
            beg=self.view.visible_region().begin()
            end=self.view.visible_region().end()

        AddLabelsCommand(self.view, self.edit, self.regex,
                         self.labels,self.label_gen,
                         beg, end, literal)


    def label_add_special(self):
        # self.labels.clear()

        self.show_panel("Enter "+self.mode.capitalize(),'',self.on_special_panel_done,
                    self.on_special_panel_change,
                    self.on_special_panel_cancel)

    def on_special_panel_done(self,input):
        if self.mode=='word':
            self.regex=input
            
            self.labels_adder()
            self.view.window().run_command("hide_panel", {"cancel": True})

            self.show_panel(self.panel_name,
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def on_special_panel_change(self,input):
        if self.mode=='char' and len(input)==1:
            self.regex=input

            self.labels_adder()
            self.view.window().run_command("hide_panel", {"cancel": True})

            self.show_panel(self.panel_name,
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def on_special_panel_cancel(self):pass


    def labels_remover(self):
        self.labels.clear()
