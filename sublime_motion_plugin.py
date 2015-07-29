'''
TODO:
1. visual mode selection from current pointer to mark. DONE
2. redraw in case multiple LABELS start with the same letter. DONE
3. Currently, in multiple cursor mode, we can only choose one mark at a time.
    I'd like to refresh the panel to select multiple marks. Like choose a range
    of marks like [1-3] or provide a list of marks to select. May have issue
    with single and double char marks.
4. change tuple to namedtuple
a. two char label will overwrite the CRLF if the word at label is shorter than
the label

6. there is only one view, not multiple view. all the view need to be self.view
    class LabelObject has view and get all views. all that needs to go away.
    there may be a function later to deal with views in different panel
    Like drawing stuff in different views

7. Redraw doesn't have to undo then replace again with a small subset. redraw
can be about changing the scope of everything else and leave the subset at the
current scope

8. Can't generate two input_panel. how to overcome this issue? another class,
    oh well.

9. how can I implement a range selection?
 select all labels in range:a-10, or aa through, 10
'''

import sublime
import sublime_plugin

from .motion import LabelObject

from .motion import BufferUndoCommand
from .motion import AddLabelsCommand
from .motion import JumpToLabelCommand
from .motion import draw_labels
from .motion import label_generator_singledouble
from .motion import draw_labels_in_range


class SublimeMotionWindowHackCommand(sublime_plugin.WindowCommand):

    def run(self, *kargs, **kwargs):
        self.mode = 'anything'
        self.panel_name = 'regex'
        self.max_input_panel = None
        self.view = self.window.active_view()
        self.literal = False
        self.multiple_selection = False

        for setting in kwargs:
            if hasattr(self, setting):
                setattr(self, setting, kwargs[setting])

        self.quick_panel = False
        self.quick_panel_multiple = self.quick_panel_till = ('1: Yes', '2: No')
        self.quick_panel_literal = ('1: Literal', '2: Not Literal')
        self.quick_panel_items = (self.quick_panel_literal,
                                  self.quick_panel_multiple,
                                  self.quick_panel_till)

        self.quick_panel_options = []
        self.show_panel()

    def quick_panel_option_rec(self, input):
        self.quick_panel_options.append(input)

    def show_panel(self):
        self.window.show_input_panel('Enter regex', '',
                                     self.on_panel_done,
                                     self.on_panel_change,
                                     self.on_panel_change)

    def on_panel_done(self, input):
        print('debug input mode.',input)
        self.view.run_command('sublime_motion',
                              {'mode': self.mode,
                               'regex': input,
                               'literal': self.literal})

    def on_panel_change(self, input):
        pass

    def on_panel_cancel(self):
        pass


class SublimeMotionCommand(sublime_plugin.TextCommand):

    def init_settings(self, edit, *kargs, **kwargs):
        self.literal = False
        self.undo = False
        self.matched_region = None
        self.labels = LabelObject()
        self.label_gen = label_generator_singledouble()
        self.edit = edit

        self.scopes = ('invalid', 'string')
        self.keys = ('focus', 'unfocus', 'background')
        self.unfocus_flag = sublime.DRAW_NO_FILL

        # panel variables
        self.panel_init_text = ''
        self.panel_name = 'Jump To'
        self.max_panel_len = 2

        # available mode:[anything,above,below,right,left,char,word]
        self.mode = "anything"
        self.regex = r'\b[^\W]'
        self.multiple_selection = False
        self.select_till = False
        self.matched_region = None
        self.range_select_mode = False
        self.range_select_list = []

        self.select_word = True
        self.current_syntax = self.view.settings().get('syntax')

        # setting the variables from the key-map
        for setting in kwargs:
            if hasattr(self, setting):
                setattr(self, setting, kwargs[setting])

        if self.mode == 'word':
            self.max_panel_len = 0

    def run(self, edit, *kargs, **kwargs):

        self.init_settings(edit, *kargs, **kwargs)

        self.labels_adder()
        self.view.window().show_input_panel(
            self.panel_name + ' ' + self.mode.capitalize(),
            self.panel_init_text,
            self.on_panel_done,
            self.on_panel_change,
            self.on_panel_cancel)

    def on_panel_done(self, input):
        if self.range_select_mode:
            self.undo_buffer()
            focus_region = []
            for label in self.range_select_list:
                region =  self.labels.get_region_by_label(label)
                if region:
                    if self.select_word:
                        region = self.view.word(region)
                    focus_region.append(region)
            if focus_region:
                JumpToLabelCommand(self.view,self.edit,self.keys,
                                   focus_region,True)
        else:
            self.matched_region = self.labels.get_region_by_label(input)
            self.undobuffer_and_jump()

    def on_panel_change(self, input):
        if not self.range_select_mode and self.max_panel_len and \
           len(input) > self.max_panel_len:
            self.terminate_panel()

        if not input:
            ''' for blank input, draw all labels '''
            draw_labels(self.view, self.keys,
                        self.scopes, self.labels,
                        self.unfocus_flag)
        elif self.range_select_mode:
            '''
            a,b,c,d0-d9,da-dz
            use rpartition, while comma is not entered yet, it's the field we're drawing/parsing
            '''

            self.range_select_list = input.rpartition(',')[0].split(',')

            focus_list = draw_labels_in_range(self.view, self.keys,
                                              self.scopes, self.labels,
                                              self.unfocus_flag,
                                              self.range_select_list)

        else:
            multiple_focuses, self.matched_region = \
                draw_labels(self.view, self.keys, self.scopes,
                            self.labels, self.unfocus_flag, input)

            if self.matched_region and len(multiple_focuses) == 1:
                self.terminate_panel()
                self.undobuffer_and_jump()

    def on_panel_cancel(self):
        self.labels.clear()
        # stopping undo by mode is very hackish, only leave it here for
        # debugging

        # need to check for either matched region or muliple focuses:
        # need a flag, if drawn, undo it.
        if not self.undo and self.matched_region:
            self.undo = BufferUndoCommand(self.view, self.edit, self.keys)

    def undobuffer_and_jump(self):
        self.undo_buffer()
        self.jump()

    def undo_buffer(self):
        if not self.undo:
            self.undo = BufferUndoCommand(self.view, self.edit, self.keys)

    def jump(self):
        if self.matched_region:
            if self.select_word:
                self.matched_region=self.view.word(self.matched_region)
            JumpToLabelCommand(self.view, self.edit, self.keys,
                               [self.matched_region.begin()],
                               self.multiple_selection, self.select_till)
            self.view.set_syntax_file(self.current_syntax)

    def terminate_panel(self):
        self.view.window().run_command("hide_panel", {"cancel": True})

    def labels_adder(self):
        self.labels.clear()

        cursor = self.view.sel()[0].begin()

        visible_begin = self.view.visible_region().begin()
        visible_end = self.view.visible_region().end()

        beg = end = None

        if self.mode == 'above':
            end = cursor
            viewing_region = sublime.Region(visible_begin, cursor)
        elif self.mode == 'below':
            beg = cursor
            viewing_region = sublime.Region(cursor, visible_end)
        elif self.mode == 'left':
            beg = self.view.line(cursor).begin()
            end = cursor
            viewing_region = sublime.Region(beg, end)
        elif self.mode == 'right':
            beg = cursor
            end = self.view.line(cursor).end()
            viewing_region = sublime.Region(beg, end)
        else:
            viewing_region = sublime.Region(visible_begin, visible_end)

        self.view.add_regions(self.keys[2], [viewing_region], '')

        AddLabelsCommand(self.view, self.edit, self.regex,
                         self.labels, self.label_gen,
                         beg, end, self.literal)

    def labels_remover(self):
        self.labels.clear()
